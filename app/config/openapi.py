"""OpenAPI/Swagger configuration with custom schema and grouping"""
from typing import Dict, Any

def get_openapi_schema() -> Dict[str, Any]:
    """Generate custom OpenAPI schema with proper grouping and documentation"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Duty Bot Admin API",
            "description": """
# Duty Bot Admin API

Comprehensive REST API for managing duty schedules, teams, and escalations.

## Authentication

All endpoints (except `/auth/token`) require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

### Getting a Token

Use the `/auth/token` endpoint to obtain a token:

```bash
curl -X POST "http://localhost:8000/api/admin/auth/token" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "user", "password": "password"}'
```

The response contains:
- `access_token` - Bearer token for subsequent requests
- `token_type` - token type (always "bearer")
- `expires_in` - token lifetime in seconds

## Base Information

### Base URL
- Development: `http://localhost:8000`
- Production: depends on deployment configuration

### API Prefix
All endpoints are located under the `/api/admin` prefix

### Error Handling
All errors are returned in the following format:
```json
{
  "detail": "Error description"
}
```

Error codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing or expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource not found)
- `500` - Internal Server Error (server error)

## Data Structures

### User
```json
{
  "id": 1,
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "is_admin": true,
  "workspace_id": 1
}
```

### Team
```json
{
  "id": 1,
  "name": "backend-team",
  "display_name": "Backend Team",
  "has_shifts": false,
  "members": [],
  "description": "Backend development team"
}
```

### Schedule (for teams without shifts)
```json
{
  "id": 1,
  "user_id": 5,
  "duty_date": "2024-12-25",
  "team_id": 1,
  "user": { "id": 5, "first_name": "John" },
  "team": { "id": 1, "name": "backend-team" }
}
```

### Shift (for teams with has_shifts=true)
```json
{
  "id": 1,
  "date": "2024-12-25",
  "team_id": 1,
  "team": { "id": 1, "name": "backend-team" },
  "users": [
    { "id": 5, "first_name": "John" },
    { "id": 7, "first_name": "Jane" }
  ]
}
```

### Escalation
```json
{
  "id": 1,
  "team_id": 1,
  "cto_id": 10,
  "team": { "id": 1, "name": "backend-team" },
  "cto_user": { "id": 10, "first_name": "Chief" }
}
```
            """,
            "version": "1.0.0",
            "contact": {
                "name": "Support",
                "email": "support@dutybot.dev"
            }
        },
        "servers": [
            {
                "url": "/",
                "description": "Current server"
            }
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter the token you get from /auth/token endpoint"
                }
            },
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "is_admin": {"type": "boolean"},
                        "workspace_id": {"type": "integer"},
                        "telegram_username": {"type": "string", "nullable": True},
                        "slack_user_id": {"type": "string", "nullable": True}
                    },
                    "required": ["id", "username", "first_name", "is_admin", "workspace_id"]
                },
                "Team": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "display_name": {"type": "string"},
                        "has_shifts": {"type": "boolean"},
                        "workspace_id": {"type": "integer"},
                        "members": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"}
                        },
                        "description": {"type": "string", "nullable": True}
                    }
                },
                "Schedule": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "duty_date": {"type": "string", "format": "date"},
                        "team_id": {"type": "integer", "nullable": True},
                        "user": {"$ref": "#/components/schemas/User"},
                        "team": {"$ref": "#/components/schemas/Team", "nullable": True}
                    },
                    "required": ["id", "user_id", "duty_date"]
                },
                "Shift": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "date": {"type": "string", "format": "date"},
                        "team_id": {"type": "integer"},
                        "team": {"$ref": "#/components/schemas/Team"},
                        "users": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"}
                        }
                    },
                    "description": "Shift assignment for teams with has_shifts=true. Multiple users can be assigned to the same shift."
                },
                "Escalation": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "team_id": {"type": "integer", "nullable": True},
                        "cto_id": {"type": "integer"},
                        "team": {"$ref": "#/components/schemas/Team", "nullable": True},
                        "cto_user": {"$ref": "#/components/schemas/User", "nullable": True}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"}
                    }
                }
            }
        },
        "tags": [
            {
                "name": "Authentication",
                "description": "Endpoints for user authentication and session management"
            },
            {
                "name": "Users",
                "description": "User information and management endpoints"
            },
            {
                "name": "Teams",
                "description": "Team management endpoints (CRUD operations)"
            },
            {
                "name": "Schedules",
                "description": "Duty schedule management and queries"
            },
            {
                "name": "Escalations",
                "description": "CTO assignments and escalation management"
            },
            {
                "name": "Admin",
                "description": "Admin-only management endpoints"
            },
            {
                "name": "Statistics",
                "description": "Statistics and reporting endpoints"
            }
        ]
    }


def custom_openapi_security() -> Dict[str, Any]:
    """Default security scheme - Bearer token required"""
    return {
        "BearerAuth": []
    }
