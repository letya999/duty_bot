# План Рефакторинга Архитектуры Duty Bot

**Статус:** 📋 В планировании
**Версия плана:** 1.0
**Дата создания:** 2025-12-24
**Текущая оценка архитектуры:** 4/10
**Целевая оценка:** 8/10

---

## 📑 Оглавление

1. [Обзор проблем](#обзор-проблем)
2. [Цели рефакторинга](#цели-рефакторинга)
3. [Фаза 1: Подготовка и планирование](#фаза-1-подготовка-и-планирование)
4. [Фаза 2: Рефакторинг обработчиков](#фаза-2-рефакторинг-обработчиков)
5. [Фаза 3: Очистка и оптимизация](#фаза-3-очистка-и-оптимизация)
6. [Фаза 4: Тестирование и документация](#фаза-4-тестирование-и-документация)
7. [График выполнения](#график-выполнения)

---

## 🔴 Обзор проблем

### Критические проблемы

1. **Монолитный файл `app/web/api.py` (1559 строк)**
   - Содержит 55+ endpoints
   - Смешивает слои: контроллер + репозиторий + бизнес-логика
   - Прямой доступ к БД в 25+ местах
   - Невозможно тестировать изолированно

2. **Прямой доступ к БД минуя сервисы**
   - 70+ мест в коде где используется `db.get()`, `db.execute()`, `db.commit()`
   - Нарушает архитектурное разделение слоев
   - Затрудняет тестирование и поддержку

3. **Дублирование логики и кода**
   - 66% функциональности дублируется между `app/web/api.py` и `app/routes/miniapp.py`
   - Логика workspace creation повторяется 8 раз в handlers
   - Логика получения текущей даты повторяется 8 раз в commands

### Средние проблемы

4. **Большие классы со множеством ответственности**
   - `CommandHandler` - 797 строк, 30+ методов
   - `TelegramHandler` - 752 строки, 9 command handlers

5. **Избыточные файлы**
   - `app/routes/miniapp.py` - дублирует функциональность `app/web/api.py`

---

## 🎯 Цели рефакторинга

- [ ] **Архитектурное разделение слоев**: Контроллеры → Сервисы → Репозитории → БД
- [ ] **Убрать дублирование кода**: Уменьшить дублирование с 66% до <10%
- [ ] **Улучшить поддерживаемость**: Разделить большие файлы на логические модули
- [ ] **Облегчить тестирование**: Сделать код тестируемым через unit-тесты
- [ ] **Улучшить читаемость**: Максимальный размер файла <300 строк

---

## 🏗️ ФАЗА 1: Подготовка и планирование

**Продолжительность:** 10-12 часов
**Приоритет:** 🔴 КРИТИЧНО
**Цель:** Создать фундамент архитектуры (репозитории, расширить сервисы)

---

### Задача 1.1: Создать репозиторный слой

**Описание:**
Создать репозитории для централизованного доступа к БД. Это позволит убрать прямые обращения к БД из контроллеров.

**Файлы к созданию:**
```
app/repositories/
├── __init__.py
├── base_repository.py      # Базовый класс с CRUD операциями
├── user_repository.py      # Доступ к пользователям
├── team_repository.py      # Доступ к командам
├── schedule_repository.py  # Доступ к расписаниям
├── workspace_repository.py # Доступ к workspace'ам
├── shift_repository.py     # Доступ к сменам
├── escalation_repository.py # Доступ к эскалациям
└── audit_repository.py     # Доступ к логам действий (если есть)
```

**Подробности реализации:**

- `BaseRepository` должен содержать стандартные CRUD методы:
  - `get_by_id(id) -> Model | None`
  - `list_all() -> list[Model]`
  - `create(data) -> Model`
  - `update(id, data) -> Model`
  - `delete(id) -> bool`

- Каждый репозиторий должен наследоваться от `BaseRepository` и добавлять специфичные методы

**Пример реализации:**

```python
# app/repositories/base_repository.py
from typing import Generic, TypeVar, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncSession, model_class: type[T]):
        self.db = db
        self.model_class = model_class

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.db.get(self.model_class, id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model_class).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: int, **kwargs) -> Optional[T]:
        obj = await self.get_by_id(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        obj = await self.get_by_id(id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True
```

```python
# app/repositories/user_repository.py
from sqlalchemy import select
from app.models import User
from .base_repository import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, User)

    async def get_by_workspace(self, workspace_id: int) -> list[User]:
        stmt = select(User).where(User.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_telegram(self, workspace_id: int, telegram_id: int) -> User | None:
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.telegram_id == telegram_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admins(self, workspace_id: int) -> list[User]:
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.is_admin == True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

**Критерии приемки:**
- [ ] Создана папка `app/repositories/`
- [ ] Реализован `BaseRepository` со всеми CRUD методами
- [ ] Созданы специализированные репозитории для: User, Team, Schedule, Workspace, Shift, Escalation
- [ ] Каждый репозиторий имеет нужные специфичные методы (примеры выше)
- [ ] Все репозитории подключены через dependency injection в `app/dependencies.py` (если его нет, создать)
- [ ] Тесты: базовые тесты для CRUD операций (optional на этом этапе)

**Метрика успеха:**
- Вся работа с БД для User, Team, Schedule теперь происходит через репозитории, не напрямую через `db.get()`

---

### Задача 1.2: Расширить сервисный слой

**Описание:**
Добавить недостающие методы в сервисы и создать новый `WorkspaceService`. Сервисы должны использовать репозитории вместо прямого доступа к БД.

**Файлы к модификации:**
- `app/services/user_service.py` - добавить методы для промоушена/демоушена пользователей
- `app/services/team_service.py` - добавить недостающие методы
- `app/services/schedule_service.py` - проверить, что используется репозиторий

**Файлы к созданию:**
- `app/services/workspace_service.py` - новый сервис для работы с workspace'ами

**Подробности реализации:**

```python
# app/services/user_service.py - добавить методы
class UserService:
    def __init__(self, user_repository: UserRepository, audit_repository: AuditRepository):
        self.user_repository = user_repository
        self.audit_repository = audit_repository

    # Новые методы:
    async def get_user_by_id(self, user_id: int, workspace_id: int) -> User | None:
        """Получить пользователя с проверкой workspace"""
        user = await self.user_repository.get_by_id(user_id)
        if user and user.workspace_id == workspace_id:
            return user
        return None

    async def promote_user(self, user_id: int, workspace_id: int, admin_id: int) -> User:
        """Промоутить пользователя в админа"""
        user = await self.get_user_by_id(user_id, workspace_id)
        if not user:
            raise ValueError("User not found in workspace")

        user = await self.user_repository.update(user_id, is_admin=True)

        # Логировать действие
        await self.audit_repository.log_action(
            workspace_id=workspace_id,
            admin_id=admin_id,
            action=f"Promoted user {user.name} to admin",
            target_user_id=user_id
        )
        return user

    async def demote_user(self, user_id: int, workspace_id: int, admin_id: int) -> User:
        """Понизить пользователя из админов"""
        user = await self.get_user_by_id(user_id, workspace_id)
        if not user:
            raise ValueError("User not found in workspace")

        user = await self.user_repository.update(user_id, is_admin=False)

        await self.audit_repository.log_action(
            workspace_id=workspace_id,
            admin_id=admin_id,
            action=f"Demoted user {user.name} from admin",
            target_user_id=user_id
        )
        return user
```

```python
# app/services/workspace_service.py - новый файл
from app.repositories import WorkspaceRepository, UserRepository
from app.models import Workspace, User

class WorkspaceService:
    def __init__(self, workspace_repo: WorkspaceRepository, user_repo: UserRepository):
        self.workspace_repo = workspace_repo
        self.user_repo = user_repo

    async def get_or_create_telegram_workspace(
        self,
        chat_id: int,
        chat_title: str | None = None
    ) -> int:
        """Получить или создать workspace из Telegram chat"""
        workspace = await self.workspace_repo.get_by_telegram_chat(chat_id)

        if not workspace:
            workspace = Workspace(
                name=chat_title or f"Chat {chat_id}",
                telegram_chat_id=chat_id,
                platform="telegram"
            )
            workspace = await self.workspace_repo.create(workspace)

        return workspace.id

    async def get_or_create_slack_workspace(
        self,
        team_id: str,
        team_name: str | None = None
    ) -> int:
        """Получить или создать workspace из Slack team"""
        workspace = await self.workspace_repo.get_by_slack_team(team_id)

        if not workspace:
            workspace = Workspace(
                name=team_name or f"Slack Team {team_id}",
                slack_team_id=team_id,
                platform="slack"
            )
            workspace = await self.workspace_repo.create(workspace)

        return workspace.id
```

**Критерии приемки:**
- [ ] Создан `app/services/workspace_service.py` с методами:
  - `get_or_create_telegram_workspace(chat_id, chat_title)`
  - `get_or_create_slack_workspace(team_id, team_name)`
- [ ] Обновлен `app/services/user_service.py` с методами:
  - `get_user_by_id(user_id, workspace_id)`
  - `promote_user(user_id, workspace_id, admin_id)`
  - `demote_user(user_id, workspace_id, admin_id)`
- [ ] Все сервисы используют репозитории, а не прямой доступ к БД
- [ ] Все сервисы логируют административные действия через audit repository
- [ ] Нет импортов `db.execute()` или прямых SQLAlchemy запросов в сервисах

**Метрика успеха:**
- Вся логика работы с workspace'ами и пользователями находится в сервисах
- Контроллеры смогут использовать сервисы вместо прямых запросов к БД

---

### Задача 1.3: Переписать app/web/api.py используя сервисы

**Описание:**
Переписать `app/web/api.py` (1559 строк) чтобы он использовал сервисы вместо прямого доступа к БД. Это все еще один файл, но код будет чище.

**Файлы к модификации:**
- `app/web/api.py` - убрать все прямые обращения к БД, использовать сервисы и репозитории

**Пример рефакторинга:**

```python
# ДО (текущее состояние):
@router.post("/users/{user_id}/promote")
async def promote_user(user_id: int, current_user: User = Depends(...)):
    if not current_user.is_admin:  # Валидация в контроллере
        raise HTTPException(status_code=403)

    target_user = await db.get(User, user_id)  # Прямой доступ к БД
    if not target_user or target_user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=400)

    target_user.is_admin = True  # Изменение модели напрямую
    await db.commit()  # Коммит в контроллере

# ПОСЛЕ (с рефакторингом):
@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),  # Валидация в dependency
    user_service: UserService = Depends(get_user_service)
):
    promoted_user = await user_service.promote_user(
        user_id=user_id,
        workspace_id=current_user.workspace_id,
        admin_id=current_user.id
    )
    return {"success": True, "user": promoted_user}
```

**Критерии приемки:**
- [ ] Все endpoints в `app/web/api.py` используют сервисы вместо прямого доступа к БД
- [ ] Нет ни одного вызова `db.get()`, `db.execute()`, `db.commit()` в контроллерах
- [ ] Все endpoints используют dependency injection для сервисов
- [ ] Валидация доступа (админ-проверки) перемещена в dependencies или сервисы
- [ ] Все тесты проходят без ошибок (если есть)
- [ ] Код по-прежнему работает на фронтенде (интеграционный тест)

**Метрика успеха:**
- `app/web/api.py` больше не содержит прямых обращений к БД
- Код контроллеров фокусируется на HTTP логике, а не на работе с данными

---

## 🔄 ФАЗА 2: Рефакторинг обработчиков

**Продолжительность:** 8-10 часов
**Приоритет:** 🟡 ВАЖНО
**Цель:** Убрать дублирование и разделить большие классы

---

### Задача 2.1: Рефакторинг telegram_handler.py

**Описание:**
Убрать дублирование кода в `app/handlers/telegram_handler.py`. Текущий код повторяет логику workspace creation и user creation в каждом command handler.

**Файлы к модификации:**
- `app/handlers/telegram_handler.py` - убрать дублирование, использовать workspace_service

**Подробности реализации:**

Создать методы в TelegramHandler для убрания дублирования:

```python
# app/handlers/telegram_handler.py

class TelegramHandler:
    def __init__(self, ..., workspace_service: WorkspaceService, user_service: UserService):
        self.workspace_service = workspace_service
        self.user_service = user_service

    async def _get_workspace_and_user(self, update, context):
        """Получить или создать workspace и пользователя (убрать дублирование)"""
        workspace_id = await self.workspace_service.get_or_create_telegram_workspace(
            chat_id=update.effective_chat.id,
            chat_title=update.effective_chat.title
        )

        user = await self.user_service.get_or_create_by_telegram(
            workspace_id=workspace_id,
            telegram_id=update.effective_user.id,
            name=update.effective_user.first_name
        )

        return workspace_id, user

    async def duty_command(self, update, context):
        """Команда /duty"""
        workspace_id, user = await self._get_workspace_and_user(update, context)
        # ... остальная логика команды

    async def team_command(self, update, context):
        """Команда /team"""
        workspace_id, user = await self._get_workspace_and_user(update, context)
        # ... остальная логика команды

    # Остальные команды используют тот же паттерн
```

**Критерии приемки:**
- [ ] Создан метод `_get_workspace_and_user()` в TelegramHandler
- [ ] Логика создания workspace перемещена в `WorkspaceService`
- [ ] Логика создания пользователя перемещена в `UserService`
- [ ] Все command handlers используют новый метод `_get_workspace_and_user()`
- [ ] Удалена функция `get_or_create_telegram_workspace()` из handler (она теперь в сервисе)
- [ ] Все обращения к БД заменены на использование сервисов
- [ ] Проверить, что все команды работают в Telegram

**Метрика успеха:**
- Код workspace creation больше не повторяется в каждом command handler
- Размер `telegram_handler.py` уменьшился на 50+ строк

---

### Задача 2.2: Рефакторинг commands/handlers.py

**Описание:**
Убрать дублирование логики получения текущей даты и разделить большой класс CommandHandler на отдельные классы.

**Файлы к модификации:**
- `app/commands/handlers.py` - убрать дублирование, создать утилиту для даты

**Подробности реализации:**

```python
# app/utils/date_utils.py - новый файл
from datetime import datetime, date
from zoneinfo import ZoneInfo
from app.config import Settings

def get_user_today(settings: Settings, date_obj: date | None = None) -> date:
    """Получить сегодняшнюю дату в timezone пользователя"""
    if date_obj is not None:
        return date_obj
    tz = ZoneInfo(settings.timezone)
    return datetime.now(tz).date()
```

```python
# app/commands/handlers.py - использовать утилиту

from app.utils.date_utils import get_user_today

class CommandHandler:
    async def handle_duty_command(self, message, user, team_service, settings):
        today = get_user_today(settings)  # Вместо повтора 8 раз
        # ...остальная логика
```

Разделить большой класс на части:

```python
# app/commands/handlers/__init__.py
from .duty_command_handler import DutyCommandHandler
from .team_command_handler import TeamCommandHandler

# app/commands/handlers/duty_command_handler.py
class DutyCommandHandler:
    async def handle(self, message, user, services):
        # Логика команды /duty (~100 строк)
        pass

# app/commands/handlers/team_command_handler.py
class TeamCommandHandler:
    async def handle(self, message, user, services):
        # Логика команды /team (~100 строк)
        pass
```

**Критерии приемки:**
- [ ] Создана утилита `app/utils/date_utils.py` с функцией `get_user_today()`
- [ ] Все повторения логики получения даты заменены на использование `get_user_today()`
- [ ] Логика каждой команды выделена в отдельный класс-handler (опционально на этом этапе, может быть в фазе 3)
- [ ] Размер `app/commands/handlers.py` уменьшился на 150+ строк
- [ ] Все команды работают в Telegram/Slack

**Метрика успеха:**
- Логика получения даты больше не повторяется
- Код более читаемый и переиспользуемый

---

### Задача 2.3: Объединить дублирующиеся API (miniapp + web)

**Описание:**
Объединить `app/web/api.py` и `app/routes/miniapp.py` в единый API с разными механизмами аутентификации.

**Файлы к модификации/созданию:**
- `app/routes/miniapp.py` - удалить (функциональность переместить)
- `app/web/api.py` - переименовать/переместить в более общее место
- `app/api/` - создать новую структуру

**Подробности реализации:**

```
app/api/
├── __init__.py
├── dependencies.py      # Общие dependencies для всех API
├── v1/
│   ├── __init__.py
│   ├── users.py        # Endpoints /api/v1/users
│   ├── teams.py        # Endpoints /api/v1/teams
│   ├── schedules.py    # Endpoints /api/v1/schedules
│   ├── shifts.py       # Endpoints /api/v1/shifts
│   ├── admin.py        # Endpoints /api/v1/admin
│   └── escalations.py  # Endpoints /api/v1/escalations
├── auth/
│   ├── __init__.py
│   ├── bearer.py       # JWT/Bearer Token аутентификация
│   ├── telegram.py     # Telegram Init Data аутентификация
│   └── dependencies.py # Общие auth dependencies
└── routes.py           # Регистрация всех роутов
```

```python
# app/api/dependencies.py
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import UserService, TeamService, ScheduleService
from app.repositories import UserRepository, TeamRepository, ScheduleRepository
from app.database import get_db

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(
        user_repository=UserRepository(db),
        audit_repository=AuditRepository(db)
    )

async def get_team_service(db: AsyncSession = Depends(get_db)) -> TeamService:
    return TeamService(team_repository=TeamRepository(db))

# и т.д. для других сервисов
```

```python
# app/api/auth/dependencies.py
async def get_current_user_from_bearer(
    token: str = Header(...),
    user_service: UserService = Depends(get_user_service)
) -> User:
    """Аутентификация через Bearer Token"""
    user = await authenticate_bearer_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

async def get_current_user_from_telegram(
    init_data: str = Header(...),
    user_service: UserService = Depends(get_user_service)
) -> User:
    """Аутентификация через Telegram Init Data"""
    user_data = verify_telegram_init_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401)
    # Получить пользователя по Telegram ID
    user = await user_service.get_by_telegram(user_data['id'])
    if not user:
        raise HTTPException(status_code=401)
    return user

# Использование в endpoints:
@router.get("/api/v1/schedules")
async def list_schedules(
    current_user: User = Depends(get_current_user)  # Работает для обоих типов auth
):
    # Один код для обоих случаев
    return await schedule_service.list_by_workspace(current_user.workspace_id)
```

**Критерии приемки:**
- [ ] Создана структура `app/api/v1/` с модулями users, teams, schedules, shifts, admin, escalations
- [ ] Все endpoints из `app/web/api.py` и `app/routes/miniapp.py` объединены в новых модулях
- [ ] Создана система аутентификации в `app/api/auth/` с поддержкой Bearer Token и Telegram Init Data
- [ ] `app/routes/miniapp.py` удален (функциональность переместить в `/api/v1/`)
- [ ] Все endpoints работают для обоих типов аутентификации
- [ ] Фронтенд (web и miniapp) работает без ошибок
- [ ] Дублирование функциональности удалено (один endpoint для обоих API)

**Метрика успеха:**
- Вместо 2 больших файлов (api.py + miniapp.py) есть 6 специализированных модулей
- Функциональность больше не дублируется
- Разные типы аутентификации работают на одних и тех же endpoints

---

## 🧹 ФАЗА 3: Очистка и оптимизация

**Продолжительность:** 6-8 часов
**Приоритет:** 🟡 УЛУЧШЕНИЯ
**Цель:** Добавить утилиты, стандартизировать обработку ошибок, улучшить валидацию

---

### Задача 3.1: Создать утилиты и decorators

**Описание:**
Создать переиспользуемые утилиты и decorators для убрания оставшегося дублирования.

**Файлы к созданию:**
- `app/utils/decorators.py` - decorators для handlers
- `app/utils/validators.py` - валидаторы данных
- `app/utils/exceptions.py` - кастомные исключения

**Подробности реализации:**

```python
# app/utils/exceptions.py
class DutyBotException(Exception):
    """Базовое исключение приложения"""
    pass

class ValidationError(DutyBotException):
    """Ошибка валидации"""
    pass

class AuthorizationError(DutyBotException):
    """Ошибка авторизации"""
    pass

class NotFoundError(DutyBotException):
    """Ресурс не найден"""
    pass

class WorkspaceNotFoundError(NotFoundError):
    """Workspace не найден"""
    pass

class UserNotFoundError(NotFoundError):
    """Пользователь не найден"""
    pass
```

```python
# app/utils/decorators.py
from functools import wraps

def with_workspace_context(func):
    """Decorator для автоматического получения workspace из update"""
    @wraps(func)
    async def wrapper(self, update, context):
        workspace_id = await self.workspace_service.get_or_create_telegram_workspace(
            chat_id=update.effective_chat.id,
            chat_title=update.effective_chat.title
        )
        user = await self.user_service.get_or_create_by_telegram(
            workspace_id=workspace_id,
            telegram_id=update.effective_user.id,
            name=update.effective_user.first_name
        )
        context.workspace_id = workspace_id
        context.current_user = user
        return await func(self, update, context)
    return wrapper

# Использование:
# @with_workspace_context
# async def duty_command(self, update, context):
#     workspace_id = context.workspace_id
#     user = context.current_user
```

```python
# app/utils/validators.py
from datetime import date, datetime
from app.utils.exceptions import ValidationError

def validate_date_range(start_date: date, end_date: date) -> None:
    """Проверить корректность диапазона дат"""
    if start_date > end_date:
        raise ValidationError("start_date must be before end_date")

def validate_user_id_in_workspace(user_id: int, workspace_id: int) -> None:
    """Проверить, что пользователь принадлежит workspace"""
    # Эта проверка должна быть в сервисе, но валидатор для быстрых проверок
    if user_id <= 0 or workspace_id <= 0:
        raise ValidationError("Invalid user_id or workspace_id")
```

**Критерии приемки:**
- [ ] Создана папка `app/utils/` со следующими модулями:
  - `date_utils.py` (из предыдущей фазы)
  - `exceptions.py` с кастомными исключениями
  - `decorators.py` с decorators для handlers
  - `validators.py` с валидаторами
- [ ] Все исключения использованы в контроллерах вместо generic HTTPException
- [ ] Decorators используются в handlers для убрания дублирования
- [ ] Код более читаемый и переиспользуемый

**Метрика успеха:**
- Нет повторяющегося кода в handlers
- Исключения структурированы и обрабатываются единообразно

---

### Задача 3.2: Стандартизировать обработку ошибок

**Описание:**
Создать единый обработчик ошибок (exception handler) для всех исключений приложения.

**Файлы к модификации:**
- `app/main.py` - добавить exception handlers

**Подробности реализации:**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.utils.exceptions import (
    DutyBotException, ValidationError, AuthorizationError, NotFoundError
)

app = FastAPI()

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": "validation_error"}
    )

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request, exc):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "error_type": "authorization_error"}
    )

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "error_type": "not_found_error"}
    )

@app.exception_handler(DutyBotException)
async def general_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": "internal_error"}
    )
```

**Критерии приемки:**
- [ ] Созданы exception handlers для всех кастомных исключений
- [ ] Exception handlers возвращают структурированный JSON с error_type
- [ ] Все контроллеры используют кастомные исключения вместо HTTPException
- [ ] Ошибки логируются (если есть logging система)
- [ ] Статус коды HTTP соответствуют типам ошибок

**Метрика успеха:**
- Обработка ошибок стандартизирована во всем приложении
- Клиенты получают структурированные ошибки с типами

---

### Задача 3.3: Добавить Pydantic schemas для валидации

**Описание:**
Создать Pydantic schemas для валидации входных данных и типизации выходных данных.

**Файлы к созданию:**
- `app/schemas/` - новая папка с Pydantic моделями
- `app/schemas/__init__.py`
- `app/schemas/user.py`
- `app/schemas/team.py`
- `app/schemas/schedule.py`
- `app/schemas/common.py` - общие схемы

**Подробности реализации:**

```python
# app/schemas/user.py
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    timezone: str = Field(default="UTC")

class UserCreate(UserBase):
    telegram_id: int | None = None
    slack_id: str | None = None

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    timezone: str | None = None

class UserResponse(UserBase):
    id: int
    workspace_id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Использование в API:
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.create_user(
        workspace_id=current_user.workspace_id,
        **user_data.model_dump()
    )
    return user
```

```python
# app/schemas/schedule.py
from pydantic import BaseModel, Field
from datetime import date

class ScheduleBase(BaseModel):
    team_id: int
    user_id: int
    date: date

class ScheduleCreate(ScheduleBase):
    notes: str | None = None

class ScheduleUpdate(BaseModel):
    user_id: int | None = None
    date: date | None = None
    notes: str | None = None

class ScheduleResponse(ScheduleBase):
    id: int
    notes: str | None = None

    class Config:
        from_attributes = True
```

**Критерии приемки:**
- [ ] Создана папка `app/schemas/` с модулями для всех основных сущностей
- [ ] Каждый endpoint использует соответствующие Pydantic schemas
- [ ] Schemas используют `Field()` для валидации и документации
- [ ] Schemas имеют `Config` с `from_attributes = True` для работы с SQLAlchemy моделями
- [ ] OpenAPI документация автоматически обновлена с описанием полей
- [ ] Валидация входных данных происходит автоматически через Pydantic

**Метрика успеха:**
- Все входные и выходные данные валидируются через Pydantic
- OpenAPI документация актуальна и понятна

---

## 📚 ФАЗА 4: Тестирование и документация

**Продолжительность:** 8-10 часов
**Приоритет:** 🟢 ФИНАЛИЗАЦИЯ
**Цель:** Добавить тесты и обновить документацию

---

### Задача 4.1: Добавить unit-тесты для сервисов

**Описание:**
Создать unit-тесты для основных сервисов с использованием pytest и моков.

**Файлы к созданию:**
```
tests/
├── __init__.py
├── conftest.py                    # Fixtures для тестов
├── fixtures.py                    # Фабрики и моки
├── unit/
│   ├── __init__.py
│   ├── test_user_service.py
│   ├── test_team_service.py
│   ├── test_schedule_service.py
│   ├── test_workspace_service.py
│   └── test_repositories.py
└── integration/
    ├── __init__.py
    └── test_api.py
```

**Подробности реализации:**

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock
from app.repositories import UserRepository, TeamRepository
from app.services import UserService, TeamService

@pytest.fixture
async def mock_db():
    """Мок БД сессии"""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
async def user_repository(mock_db):
    return UserRepository(mock_db)

@pytest.fixture
async def user_service(user_repository):
    audit_repo = MagicMock()
    return UserService(user_repository, audit_repo)

# tests/unit/test_user_service.py
import pytest
from app.models import User
from app.utils.exceptions import NotFoundError

@pytest.mark.asyncio
class TestUserService:
    async def test_get_user_by_id_success(self, user_service, user_repository):
        # Arrange
        user_id = 1
        workspace_id = 100
        expected_user = User(id=user_id, workspace_id=workspace_id, name="Test User")
        user_repository.get_by_id = AsyncMock(return_value=expected_user)

        # Act
        result = await user_service.get_user_by_id(user_id, workspace_id)

        # Assert
        assert result == expected_user
        user_repository.get_by_id.assert_called_once_with(user_id)

    async def test_get_user_by_id_not_found(self, user_service, user_repository):
        # Arrange
        user_repository.get_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(NotFoundError):
            await user_service.get_user_by_id(999, 100)

    async def test_promote_user_success(self, user_service, user_repository):
        # Arrange
        user_id = 1
        workspace_id = 100
        user = User(id=user_id, workspace_id=workspace_id, is_admin=False)
        user_repository.get_by_id = AsyncMock(return_value=user)
        user_repository.update = AsyncMock(return_value=User(id=user_id, is_admin=True))

        # Act
        result = await user_service.promote_user(user_id, workspace_id, admin_id=2)

        # Assert
        assert result.is_admin is True
        user_repository.update.assert_called_once()
```

**Критерии приемки:**
- [ ] Создана папка `tests/` с conftest.py
- [ ] Написаны unit-тесты для следующих сервисов:
  - `UserService` (минимум 5 тестов)
  - `TeamService` (минимум 3 теста)
  - `ScheduleService` (минимум 4 теста)
  - `WorkspaceService` (минимум 3 теста)
- [ ] Написаны тесты для репозиториев (CRUD операции)
- [ ] Все тесты используют mocks/fixtures
- [ ] Тесты запускаются с помощью `pytest`
- [ ] Покрытие тестами >70% для сервисов

**Метрика успеха:**
- Все сервисы имеют unit-тесты
- Можно изменять реализацию сервисов без страха сломать функциональность

---

### Задача 4.2: Добавить интеграционные тесты для API

**Описание:**
Создать интеграционные тесты для основных API endpoints.

**Файлы к модификации:**
- `tests/integration/test_api.py` - интеграционные тесты

**Подробности реализации:**

```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User, Team, Workspace

@pytest.mark.asyncio
class TestUserAPI:
    async def test_create_user(self, async_client: AsyncClient, admin_token: str):
        # Arrange
        user_data = {
            "name": "New User",
            "email": "user@example.com",
            "timezone": "Europe/Moscow"
        }

        # Act
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "New User"

    async def test_list_users(self, async_client: AsyncClient, admin_token: str):
        # Act
        response = await async_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
class TestScheduleAPI:
    async def test_create_schedule(self, async_client: AsyncClient, admin_token: str):
        # Arrange
        schedule_data = {
            "team_id": 1,
            "user_id": 1,
            "date": "2025-12-25"
        }

        # Act
        response = await async_client.post(
            "/api/v1/schedules",
            json=schedule_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Assert
        assert response.status_code == 201
```

**Критерии приемки:**
- [ ] Написаны интеграционные тесты для основных endpoints:
  - User API (create, list, update, delete)
  - Team API (create, list, update, delete)
  - Schedule API (create, list, update, delete)
- [ ] Тесты используют реальную БД (в памяти для тестов)
- [ ] Тесты проверяют аутентификацию и авторизацию
- [ ] Все тесты проходят успешно

**Метрика успеха:**
- Интеграционные тесты гарантируют, что API работает правильно

---

### Задача 4.3: Обновить документацию архитектуры

**Описание:**
Создать документацию о новой архитектуре и гайды для разработчиков.

**Файлы к созданию:**
```
docs/
├── REFACTORING_PLAN.md      (этот файл)
├── ARCHITECTURE.md          # Описание слоев и компонентов
├── API_GUIDE.md            # Гайд по API
├── DEVELOPMENT.md          # Гайд для разработчиков
├── TESTING.md              # Гайд по тестированию
└── DEPLOYMENT.md           # Гайд по развертыванию (если нужно)
```

**Содержимое:**

```markdown
# docs/ARCHITECTURE.md

## Архитектура приложения

### Слои архитектуры

1. **Presentation Layer (Контроллеры)**
   - `app/web/api/` - REST API endpoints
   - `app/handlers/` - Telegram/Slack обработчики
   - Ответственность: Парсинг HTTP запросов, HTTP ответы, аутентификация

2. **Business Logic Layer (Сервисы)**
   - `app/services/` - Бизнес-логика
   - Ответственность: Валидация, обработка данных, координация операций

3. **Data Access Layer (Репозитории)**
   - `app/repositories/` - Работа с БД
   - Ответственность: CRUD операции, SQL запросы

4. **Domain Layer (Модели)**
   - `app/models.py` - SQLAlchemy модели
   - Ответственность: Описание структуры данных
```

**Критерии приемки:**
- [ ] Создан файл `docs/ARCHITECTURE.md` с описанием архитектуры
- [ ] Создан файл `docs/DEVELOPMENT.md` с гайдом для разработчиков
- [ ] Создан файл `docs/TESTING.md` с гайдом по тестированию
- [ ] Документация актуальна и понятна
- [ ] В документации есть примеры кода

**Метрика успеха:**
- Новые разработчики смогут понять архитектуру за 30 минут чтения документации

---

## 📅 График выполнения

| Фаза | Задачи | Часы | Неделя |
|------|--------|------|--------|
| **1** | 1.1 + 1.2 + 1.3 | 10-12 | 1-2 |
| **2** | 2.1 + 2.2 + 2.3 | 8-10 | 2-3 |
| **3** | 3.1 + 3.2 + 3.3 | 6-8 | 3 |
| **4** | 4.1 + 4.2 + 4.3 | 8-10 | 4 |
| **ИТОГО** | | **32-40 часов** | **4 недели** |

---

## ✅ Критерии приемки (финальные)

Рефакторинг считается завершенным, когда:

1. **Архитектурные критерии:**
   - [ ] Нет прямого доступа к БД из контроллеров (все через репозитории)
   - [ ] Бизнес-логика находится в сервисах, а не в контроллерах
   - [ ] Максимальный размер файла <300 строк
   - [ ] Нет дублирования кода >5 строк (похожие логики извлечены в утилиты)
   - [ ] Зависимости идут только в одну сторону: контроллеры → сервисы → репозитории → БД

2. **Функциональные критерии:**
   - [ ] Все endpoints работают (web API + Telegram handlers + Slack handlers)
   - [ ] Все фиче, что были до рефакторинга, все еще работают
   - [ ] Нет регрессии функциональности

3. **Критерии качества кода:**
   - [ ] Код проходит linting (если используется)
   - [ ] Все type hints добавлены
   - [ ] Документация актуальна

4. **Критерии тестирования:**
   - [ ] Unit-тесты для сервисов (>70% покрытие)
   - [ ] Интеграционные тесты для API
   - [ ] Все тесты проходят успешно

---

## 📊 Метрики успеха (до и после)

| Метрика | До | После | Цель |
|---------|-------|-------|------|
| Макс размер файла | 1559 строк | <300 строк | ✅ |
| Прямой доступ к БД | 70+ мест | 0 мест | ✅ |
| Дублирование кода | 66% | <10% | ✅ |
| Размер репозиториев | 0 файлов | 8 файлов | ✅ |
| Покрытие тестами | 0% | >70% | ✅ |
| **Архитектурная оценка** | **4/10** | **8/10** | **✅** |

---

## 📝 Примечания

- Каждая фаза может быть выполнена независимо, но рекомендуется выполнять по порядку
- После каждой задачи делать commit с описанием изменений
- Регулярно запускать тесты и проверять, что функциональность не сломана
- Если возникают проблемы, документировать их и обсуждать в issue

---

**План создан:** 2025-12-24
**Статус:** 📋 В планировании
**Следующий шаг:** Одобрение плана и начало Фазы 1, Задача 1.1
