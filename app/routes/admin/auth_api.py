"""Authentication API endpoints for token generation and validation"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from app.auth import session_manager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Authentication"])

settings = get_settings()


class TokenRequest(BaseModel):
    """Token request model"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Get authentication token",
    description="""
    Получить токен для аутентификации в API.

    Используйте этот endpoint для получения Bearer token, необходимого для всех защищенных endpoints.

    **Параметры:**
    - `username`: Имя пользователя
    - `password`: Пароль пользователя

    **Возвращает:**
    - `access_token`: Bearer token для использования в Authorization заголовке
    - `token_type`: Тип токена (всегда "bearer")
    - `expires_in`: Время жизни токена в секундах

    **Примеры:**

    ```bash
    curl -X POST "http://localhost:8000/api/admin/auth/token" \\
      -H "Content-Type: application/json" \\
      -d '{
        "username": "john_doe",
        "password": "secret_password"
      }'
    ```

    **Ответ:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 86400
    }
    ```

    Полученный token используйте в Authorization заголовке:
    ```bash
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """,
    responses={
        200: {
            "description": "Token успешно получен",
            "model": TokenResponse
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid username or password"}
                }
            }
        }
    }
)
async def get_token(request: TokenRequest = Body(...)):
    """
    Generate authentication token for API access.

    Demo endpoint - returns a test token. In production, validate against user database.
    """
    # Demo validation - in production, query database and validate password hash
    if request.username == "admin" and request.password == "admin":
        # Create session token
        token = session_manager.create_session({
            'user_id': 1,
            'username': request.username,
            'is_admin': True
        })

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=86400  # 24 hours
        )

    raise HTTPException(
        status_code=401,
        detail="Invalid username or password"
    )


@router.post(
    "/auth/token/validate",
    summary="Validate authentication token",
    description="""
    Проверить валидность токена.

    **Headers:**
    - `Authorization`: Bearer token

    **Возвращает:**
    - `valid`: boolean - валидность токена
    - `user_id`: ID пользователя (если валидный)
    - `expires_at`: Время истечения токена

    **Примеры:**

    ```bash
    curl -X POST "http://localhost:8000/api/admin/auth/token/validate" \\
      -H "Authorization: Bearer <token>"
    ```
    """,
    responses={
        200: {
            "description": "Token validation result",
            "content": {
                "application/json": {
                    "example": {
                        "valid": True,
                        "user_id": 1,
                        "expires_at": "2024-12-25T10:30:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Invalid or expired token"
        }
    }
)
async def validate_token(authorization: str = None):
    """Validate if token is still valid"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1]
    session = session_manager.validate_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "valid": True,
        "user_id": session.get('user_id'),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
