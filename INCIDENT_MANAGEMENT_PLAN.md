# MVP: Управление инцидентами - Полный план реализации

## 1. ОБЗОР

Система управления инцидентами с поддержкой:
- **Гибкой приоритизации** через матрицу Severity/Priority
- **Управления дежурством** с ротацией по дням (существующий функционал)
- **Управления ролями в команде** (Dev-on-call, QA-on-call и т.д., кастомные для каждой команды)
- **Конструктора эскалации инцидентов** с UI builder
- **Работы через Slack/Telegram боты**
- **Вебморды для конфигурации**

---

## 2. РАСШИРЕНИЕ БАЗЫ ДАННЫХ

### 2.1 Новые таблицы

#### `team_role` (отдельная таблица)
Роли, которые команда может определять самостоятельно.

```python
class TeamRole(Base):
    """Роль в команде (Dev-on-call, QA-on-call, TL и т.д.)"""
    __tablename__ = 'team_role'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)

    key = Column(String, nullable=False)  # dev-on-call, qa-on-call, tl (уникален в команде)
    name = Column(String, nullable=False)  # отображаемое имя "Разработчик" "Тестировщик"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship('Team', back_populates='roles')
    members = relationship('TeamRoleMember', back_populates='role', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('team_id', 'key', name='team_role_team_key_unique'),
    )
```

#### `team_role_member` (отдельная таблица)
Привязка пользователей к ролям в команде.

```python
class TeamRoleMember(Base):
    """Пользователь в роли команды"""
    __tablename__ = 'team_role_member'

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('team_role.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    role = relationship('TeamRole', back_populates='members')
    user = relationship('User')

    __table_args__ = (
        UniqueConstraint('role_id', 'user_id', name='team_role_member_unique'),
    )
```

#### `component` (новая таблица)
Справочник компонентов приложения.

```python
class Component(Base):
    """Компонент приложения (Авторизация, Чаты, Платежи и т.д.)"""
    __tablename__ = 'component'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)

    key = Column(String, nullable=False)  # auth, messaging, payments (уникален в workspace)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    default_priority = Column(String, nullable=False)  # P1, P2, P3

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace')
    team = relationship('Team')
    incidents = relationship('Incident', back_populates='component')

    __table_args__ = (
        UniqueConstraint('workspace_id', 'key', name='component_workspace_key_unique'),
    )
```

#### `prioritization_config` (новая таблица)
Матрица приоритизации для workspace.

```python
class PrioritizationConfig(Base):
    """Конфигурация матрицы приоритизации (Severity × Priority)"""
    __tablename__ = 'prioritization_config'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, unique=True, index=True)

    # Матрица в JSON: ключ = "S1:P1,P2", значение = разрешено ли
    # Пример: {"S1": ["P1"], "S2": ["P1", "P2"], "S3": ["P2", "P3"], "S4": ["P3"]}
    matrix = Column(JSON, nullable=False)

    # Конфигурация приоритетов
    allow_p3 = Column(Boolean, default=False)  # Можно ли создавать P3 инциденты

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace')
```

#### `escalation_config` (новая таблица)
Конфигурация эскалации для команды и приоритета.

```python
class EscalationConfig(Base):
    """Конфигурация эскалации для (Team, Priority)"""
    __tablename__ = 'escalation_config'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    priority = Column(String, nullable=False)  # P1, P2

    # JSON с шагами эскалации
    # [{
    #   "order": 1,
    #   "role_keys": ["dev-on-call", "qa-on-call"],
    #   "parallel": true,
    #   "timer_minutes": 10,
    #   "acknowledgment_method": "reaction_or_command",  # или только команда бота
    #   "on_timeout": {
    #     "action": "escalate",
    #     "notify_in_chat": "свяжитесь по номеру",
    #     "timer_minutes": 5,
    #     "next_step": 2
    #   }
    # }]
    steps = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship('Team')

    __table_args__ = (
        UniqueConstraint('team_id', 'priority', name='escalation_config_team_priority_unique'),
    )
```

### 2.2 Расширение существующих таблиц

#### `team` (расширение)
```python
# Добавить в существующий Team:
roles = relationship('TeamRole', back_populates='team', cascade='all, delete-orphan')
incidents = relationship('Incident', back_populates='team')
escalation_configs = relationship('EscalationConfig', back_populates='team', cascade='all, delete-orphan')
```

#### `incident` (полная переделка)
```python
class Incident(Base):
    """Инцидент с полной историей и статусами"""
    __tablename__ = 'incident'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False, index=True)  # Последовательный номер

    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=True, index=True)
    component_id = Column(Integer, ForeignKey('component.id'), nullable=True, index=True)

    # Основная информация
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Приоритизация
    severity = Column(String, nullable=True)  # S1, S2, S3, S4 (может быть null если не используется)
    priority = Column(String, nullable=False, index=True)  # P1, P2, P3

    # Статус
    status = Column(String, nullable=False, default='detected', index=True)
    # Возможные значения:
    # detected → confirmed → in_progress → resolved → post_mortem_pending → documented → closed

    # Времена жизни инцидента
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)  # когда начали работать
    resolved_at = Column(DateTime, nullable=True)  # когда решили проблему
    acknowledged_by_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace')
    organization = relationship('Organization')
    team = relationship('Team', back_populates='incidents')
    component = relationship('Component', back_populates='incidents')
    acknowledged_by = relationship('User')
    escalation_steps = relationship('IncidentEscalationStep', back_populates='incident', cascade='all, delete-orphan')
    events = relationship('IncidentEvent', back_populates='incident', cascade='all, delete-orphan')
```

#### `incident_escalation_step` (новая таблица)
```python
class IncidentEscalationStep(Base):
    """История шагов эскалации для инцидента"""
    __tablename__ = 'incident_escalation_step'

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey('incident.id'), nullable=False, index=True)

    step_order = Column(Integer, nullable=False)  # Порядок шага (1, 2, 3...)
    role_key = Column(String, nullable=False)  # dev-on-call, qa-on-call и т.д.
    person_id = Column(Integer, ForeignKey('user.id'), nullable=True)  # Кто был уведомлен

    # Статусы: pending → acknowledged → escalated
    status = Column(String, nullable=False)

    # Тайминг
    notified_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship('Incident', back_populates='escalation_steps')
    person = relationship('User')
```

#### `incident_event` (новая таблица)
```python
class IncidentEvent(Base):
    """Лента событий для инцидента (audit trail)"""
    __tablename__ = 'incident_event'

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey('incident.id'), nullable=False, index=True)

    # Тип события
    event_type = Column(String, nullable=False)
    # status_changed, escalated, acknowledged, severity_changed, etc

    # Старое и новое значение (для status_changed и т.д.)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)

    # Кто сделал действие
    actor_id = Column(Integer, ForeignKey('user.id'), nullable=True)

    # Дополнительные детали в JSON
    details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    incident = relationship('Incident', back_populates='events')
    actor = relationship('User')
```

#### `workspace` (расширение)
```python
# Добавить в существующий Workspace:
prioritization_config = relationship('PrioritizationConfig', uselist=False, cascade='all, delete-orphan')
incidents = relationship('Incident', back_populates='workspace')
```

---

## 3. API ENDPOINTS

### 3.1 Компоненты `/api/components`

```
POST   /api/components
  Тело: { key, name, description, team_id, default_priority }
  Возврат: { id, key, name, team_id, default_priority, created_at }

GET    /api/components
  Параметры: ?team_id={id}, ?workspace_id={id}
  Возврат: List[Component]

GET    /api/components/{id}
  Возврат: Component

PUT    /api/components/{id}
  Тело: { name, description, default_priority }
  Возврат: Component

DELETE /api/components/{id}
  Возврат: 204 No Content
```

### 3.2 Инциденты `/api/incidents`

```
POST   /api/incidents
  Тело: { name, description, component_id, severity?, priority? }
  Логика:
    - Если указан component_id → берётся team_id от компонента
    - Если указана severity → автоматический расчёт priority по матрице
    - Если не указана severity → берётся из UI (только priority)
  Возврат: { id, number, name, status, priority, team_id, created_at }

GET    /api/incidents
  Параметры: ?status={detected|confirmed|...}, ?priority={P1|P2|P3}, ?team_id={}, ?component_id={}
  Возврат: List[Incident]

GET    /api/incidents/{id}
  Возврат: {
    id, number, name, description,
    component, team, severity, priority, status,
    created_at, confirmed_at, started_at, resolved_at,
    acknowledged_by, acknowledged_at,
    escalation_steps: [ { step_order, role_key, person, status, notified_at, acknowledged_at } ],
    events: [ { event_type, old_value, new_value, actor, created_at } ]
  }

PUT    /api/incidents/{id}/status
  Тело: { new_status }
  Логика: обновить статус + создать IncidentEvent
  Возврат: Incident

PUT    /api/incidents/{id}/priority
  Тело: { severity?, priority? }
  Логика: переоценить приоритет + создать IncidentEvent
  Возврат: Incident

PUT    /api/incidents/{id}/acknowledge
  Логика: подтвердить первый шаг эскалации, перевести в in_progress
  Возврат: Incident
```

### 3.3 Приоритизация `/api/prioritization`

```
GET    /api/prioritization/matrix
  Параметры: ?workspace_id={id}
  Возврат: {
    matrix: { "S1": ["P1"], "S2": ["P1", "P2"], ... },
    allow_p3: false
  }

PUT    /api/prioritization/matrix
  Тело: { matrix, allow_p3 }
  Логика: обновить матрицу, валидировать что S1:P1 всегда есть и т.д.
  Возврат: PrioritizationConfig
```

### 3.4 Роли команды `/api/teams/{team_id}/roles`

```
POST   /api/teams/{team_id}/roles
  Тело: { key, name }
  Возврат: { id, key, name, created_at }

GET    /api/teams/{team_id}/roles
  Возврат: List[TeamRole]

GET    /api/teams/{team_id}/roles/{role_id}
  Возврат: { id, key, name, members: [ { id, display_name, ... } ] }

PUT    /api/teams/{team_id}/roles/{role_id}
  Тело: { name, members: [user_id, ...] }
  Логика: обновить имя роли и членов
  Возврат: TeamRole

DELETE /api/teams/{team_id}/roles/{role_id}
  Возврат: 204 No Content

POST   /api/teams/{team_id}/roles/{role_id}/members
  Тело: { user_id }
  Логика: добавить пользователя в роль
  Возврат: TeamRoleMember

DELETE /api/teams/{team_id}/roles/{role_id}/members/{user_id}
  Логика: удалить пользователя из роли
  Возврат: 204 No Content

GET    /api/teams/{team_id}/roles/{role_key}/current-on-duty
  Параметры: ?date={YYYY-MM-DD}
  Логика: получить кто сегодня дежурит в роли
         используя RotationConfig + Schedule
         или просто первого члена роли если нет расписания
  Возврат: { user_id, display_name, ... }
```

### 3.5 Конфигурация эскалации `/api/teams/{team_id}/escalation`

```
GET    /api/teams/{team_id}/escalation/{priority}
  Возврат: {
    id, team_id, priority, steps: [
      { order, role_keys, parallel, timer_minutes, acknowledgment_method, on_timeout }
    ]
  }

PUT    /api/teams/{team_id}/escalation/{priority}
  Тело: { steps: [ { order, role_keys, parallel, timer_minutes, ... } ] }
  Логика: валидировать что все role_keys существуют в TeamRole
  Возврат: EscalationConfig

GET    /api/teams/{team_id}/escalation
  Возврат: List[EscalationConfig]  # все конфиги для всех приоритетов
```

### 3.6 История эскалации `/api/incidents/{incident_id}/escalation`

```
GET    /api/incidents/{incident_id}/escalation
  Возврат: List[IncidentEscalationStep] с информацией о каждом шаге

GET    /api/incidents/{incident_id}/events
  Возврат: List[IncidentEvent]  # лента всех изменений
```

---

## 4. БОТЫ (Slack + Telegram)

### 4.1 Расширение существующих handlers

**Файлы:**
- `app/handlers/slack_handler.py` — добавить команды для инцидентов
- `app/handlers/telegram_handler.py` — добавить команды для инцидентов

### 4.2 Slack команды

```
/incident create
  → Интерактивный диалог в потоке
    1. Название: [text]
    2. Компонент: [dropdown] → выбор из справочника
    3. Severity (опционально): [dropdown] → S1, S2, S3, S4
    4. [Создать]
  → Создан инцидент #1234
  → В чат команды (channel от компонента.team):
     "🚨 P1 ИНЦИДЕНТ: Авторизация не работает (инцидент #1234)
      Дежурные: @dev-on-call (сегодня: Юрий), @qa-on-call (сегодня: Анна)
      [✓ Принял] [📞 Не могу] [🚫 Это не мой]"

/incident list [status]
  → Список активных инцидентов в формате:
     #1234 P1 Авторизация не работает (detected, 10 мин назад)
     #1233 P2 Чаты не открываются (in_progress, работает 5 мин)

/incident status <ID>
  → Полная информация об инциденте с графом эскалации

/incident ack
  → Ответ на сообщение об уведомлении
  → Переводит инцидент в in_progress
  → Отмечает шаг 1 как acknowledged

/incident close <ID> [--reason "фикс выкачен"]
  → Закрыть инцидент (перевести в resolved)

@bot duty [team_name]
  → Показать кто на дежурстве в команде
  → Использует TeamRole + RotationConfig + Schedule
  → "Дежурные Red Team: Dev-on-call — Юрий, QA-on-call — Анна"
```

### 4.3 Telegram команды

```
/incident_create
  → Интерактивное меню:
    1. Название: [text]
    2. Компонент: [inline buttons] → выбор
    3. Severity: [inline buttons] → опционально
    4. [Создать]

/incident_list [status]
  → Список с inline кнопками для быстрого доступа

/incident_status <ID>
  → Полная информация в сообщении

/incident_ack <ID>
  → Принял в работу

/incident_close <ID>
  → Закрыть инцидент

/duty [team_name]
  → Кто на дежурстве
```

---

## 5. ВЕБМОРДА (React)

### 5.1 Структура папок

```
webapp/src/
├── pages/
│   ├── incidents/
│   │   ├── IncidentsPage.tsx          # Список инцидентов
│   │   ├── IncidentDetailPage.tsx     # Просмотр с графом эскалации
│   │   └── IncidentFormModal.tsx      # Форма создания
│   │
│   ├── components-list/
│   │   └── ComponentsPage.tsx         # Справочник компонентов
│   │
│   ├── settings/
│   │   ├── PrioritizationPage.tsx     # Матрица приоритизации
│   │   └── TeamsRolesPage.tsx         # Управление ролями в команде
│   │
│   └── escalation/
│       └── EscalationBuilderPage.tsx  # UI конструктор эскалации
│
├── components/
│   ├── incidents/
│   │   ├── IncidentTable.tsx          # Таблица инцидентов
│   │   ├── IncidentForm.tsx           # Форма создания
│   │   ├── EscalationGraph.tsx        # Визуализация эскалации
│   │   └── IncidentTimeline.tsx       # Лента событий
│   │
│   ├── escalation/
│   │   ├── EscalationBuilder.tsx      # UI builder
│   │   ├── EscalationStep.tsx         # Компонент шага
│   │   └── EscalationPreview.tsx      # Предпросмотр графа
│   │
│   └── settings/
│       ├── PriorityMatrix.tsx         # Интерактивная матрица
│       └── TeamRolesManager.tsx       # Управление ролями
│
└── services/
    ├── incidentsApi.ts                # API для инцидентов
    ├── componentsApi.ts               # API для компонентов
    ├── rolesApi.ts                    # API для ролей
    └── escalationApi.ts               # API для эскалации
```

### 5.2 Страницы и функциональность

#### Инциденты (`/incidents`)

**Список:**
- Таблица: ID | Название | Компонент | Priority | Status | Время | [View]
- Фильтры: Status, Priority, Team, Component, Дата (слева в сайдбаре)
- [+ Создать инцидент]
- Сортировка по времени создания, приоритету

**Просмотр (`/incidents/{id}`):**
- Основная информация (название, описание, компонент, приоритет, статус)
- **Граф эскалации** (визуальное дерево):
  ```
  Шаг 1: Dev-on-call (Юрий) ✓ ответил за 2 мин
         QA-on-call (Анна) ✓ ответила за 3 мин
         ↓
  Шаг 2: Team Lead (Сергей) ⏳ в ожидании (8 мин)
  ```
- Лента событий (кто что делал и когда)
- Метрики: MTTR, время в каждом статусе
- Кнопки действия: Change status, Close

#### Компоненты (`/components`)

**Таблица:**
- Название | Ключ | Team | Default Priority | [Edit] [Delete]
- [+ Добавить компонент]

**Форма создания/редактирования:**
- Ключ (не меняется после создания)
- Название
- Описание
- Команда [dropdown]
- Default Priority [dropdown]

#### Приоритизация (`/settings/prioritization`)

**Интерактивная матрица:**
```
         P1      P2      P3
S1      ✓       ✗       ✗
S2      ✓       ✓       ✗
S3      ✗       ✓       ✓
S4      ✗       ✗       ✓
```
- Клик на ячейку → выбрать приоритет (✓ или ✗)
- Галочка "Разрешить P3 инциденты"
- [Сохранить]

#### Роли команды (`/teams/{team_id}/roles`)

**Таблица ролей:**
- Ключ | Название | Члены | [Edit] [Delete]
- [+ Добавить роль]

**Редактирование роли:**
- Название
- Члены [multi-select dropdown]
- [Сохранить]

#### Конструктор эскалации (`/teams/{team_id}/escalation/{priority}`)

**UI Builder:**
```
[Priority: P1] [Priority: P2] ← табы

[+ Добавить шаг]

┌─── ШАГ 1 ──────────────────────────────┐
│ Роли: [✓] dev-on-call [✓] qa-on-call  │
│ Параллельно: [✓]                       │
│ Таймер: ●────────────(10 мин)          │
│ Условие ответа:                        │
│   [✓] Реакция 👍                       │
│   [✓] Команда /ack                     │
│ На timeout:                             │
│   [○ Продолжить ждать]                 │
│   [●] Написать сообщение в чат         │
│       "Свяжитесь по номеру"            │
│       Таймер: 5 мин                    │
│   [○] Позвонить (интеграция)           │
│   ↓ Перейти на шаг: 2                  │
│ [↑ ↓] [Delete]                         │
└─────────────────────────────────────────┘

┌─── ШАГ 2 ──────────────────────────────┐
│ Роли: [✓] tl                           │
│ Таймер: 10 мин                         │
│ На timeout: [Перейти на ШАГ 3]         │
│ [↑ ↓] [Delete]                         │
└─────────────────────────────────────────┘

[Сохранить] [Тест] [Предпросмотр графа]
```

**Предпросмотр графа** (визуальное дерево эскалации)

---

## 6. СЕРВИСЫ (app/services/)

### 6.1 IncidentService

```python
class IncidentService:
    async def create_incident(
        workspace_id: int,
        name: str,
        description: str,
        component_id: int,
        severity: str = None,
        priority: str = None
    ) -> Incident
        # Логика:
        # 1. Получить компонент и team_id
        # 2. Если severity указана → вычислить priority по матрице
        # 3. Если priority не указана → взять default от компонента
        # 4. Создать инцидент
        # 5. Создать IncidentEvent (created)
        # 6. Запустить эскалацию (первый шаг)

    async def get_incident(incident_id: int) -> Incident
        # Получить инцидент с полной историей

    async def list_incidents(
        workspace_id: int,
        status: str = None,
        priority: str = None,
        team_id: int = None,
        component_id: int = None
    ) -> List[Incident]

    async def change_status(incident_id: int, new_status: str) -> Incident
        # Обновить статус + создать IncidentEvent

    async def recalculate_priority(
        incident_id: int,
        severity: str = None,
        priority: str = None
    ) -> Incident
        # Переоценить приоритет + создать IncidentEvent

    async def acknowledge_incident(incident_id: int, user_id: int) -> Incident
        # Подтвердить первый шаг эскалации
        # Перевести в in_progress
        # Создать IncidentEvent
```

### 6.2 EscalationService

```python
class EscalationService:
    async def get_config(team_id: int, priority: str) -> EscalationConfig

    async def save_config(
        team_id: int,
        priority: str,
        steps: List[dict]
    ) -> EscalationConfig
        # Валидировать что все role_keys существуют в TeamRole

    async def start_escalation(incident_id: int) -> None
        # Запустить первый шаг эскалации
        # Получить конфиг для (team, priority)
        # Создать IncidentEscalationStep для каждого role_key
        # Отправить уведомления в Slack/Telegram
        # Запустить таймеры

    async def handle_acknowledgment(
        incident_id: int,
        step_order: int,
        user_id: int
    ) -> None
        # Подтвердить шаг эскалации
        # Обновить IncidentEscalationStep
        # Если это первый шаг → перевести инцидент в in_progress

    async def escalate_to_next_step(incident_id: int, current_step_order: int) -> None
        # Получить конфиг эскалации
        # Найти следующий шаг
        # Создать новый IncidentEscalationStep
        # Отправить уведомления
        # Запустить таймер

    async def handle_timeout(incident_id: int, step_order: int) -> None
        # Обработать timeout на шаге эскалации
        # Выполнить действие из on_timeout конфига
```

### 6.3 TeamRoleService

```python
class TeamRoleService:
    async def create_role(team_id: int, key: str, name: str) -> TeamRole

    async def add_member_to_role(role_id: int, user_id: int) -> None

    async def remove_member_from_role(role_id: int, user_id: int) -> None

    async def get_role_members(role_id: int) -> List[User]

    async def get_current_on_duty(
        team_id: int,
        role_key: str,
        date: date = None
    ) -> User
        # Логика:
        # 1. Получить TeamRole по team_id и role_key
        # 2. Получить RotationConfig для team_id
        # 3. Если включена ротация → найти Schedule на дату
        # 4. Если не включена ротация → вернуть первого члена роли
        # 5. Если выходной → вернуть None или следующего
```

### 6.4 ComponentService

```python
class ComponentService:
    async def create_component(
        workspace_id: int,
        team_id: int,
        key: str,
        name: str,
        description: str = None,
        default_priority: str = None
    ) -> Component

    async def list_components(workspace_id: int) -> List[Component]

    async def get_component(component_id: int) -> Component

    async def update_component(component_id: int, **kwargs) -> Component

    async def delete_component(component_id: int) -> None
```

### 6.5 PrioritizationService

```python
class PrioritizationService:
    async def get_config(workspace_id: int) -> PrioritizationConfig

    async def save_config(workspace_id: int, matrix: dict, allow_p3: bool) -> PrioritizationConfig
        # Валидировать матрицу
        # S1 должна быть в P1
        # P3 должна быть во всех S если allow_p3=True

    async def calculate_priority(
        workspace_id: int,
        severity: str,
        priority: str = None
    ) -> str
        # Если severity указана → вычислить priority по матрице
        # Если priority уже указана → валидировать что это допустимая комбинация
```

---

## 7. РЕПОЗИТОРИИ (app/repositories/)

### 7.1 Новые репозитории

```
app/repositories/
├── incident_repository.py      # CRUD для Incident, IncidentEvent, IncidentEscalationStep
├── component_repository.py     # CRUD для Component
├── team_role_repository.py     # CRUD для TeamRole, TeamRoleMember
├── escalation_config_repository.py  # CRUD для EscalationConfig
└── prioritization_repository.py     # CRUD для PrioritizationConfig
```

Каждый репозиторий должен иметь:
- `create()`
- `get_by_id()`
- `list()` с фильтрами
- `update()`
- `delete()`

---

## 8. МИГРАЦИИ БД

Создать миграции Alembic для:
1. Создание таблицы `team_role`
2. Создание таблицы `team_role_member`
3. Создание таблицы `component`
4. Создание таблицы `prioritization_config`
5. Создание таблицы `escalation_config`
6. Модификация таблицы `incident`
7. Создание таблицы `incident_escalation_step`
8. Создание таблицы `incident_event`
9. Добавление relations в `team` и `workspace`

---

## 9. ТЕСТИРОВАНИЕ

### 9.1 Unit тесты (tests/unit/)

```
tests/unit/
├── services/
│   ├── test_incident_service.py
│   ├── test_escalation_service.py
│   ├── test_team_role_service.py
│   ├── test_component_service.py
│   └── test_prioritization_service.py
│
├── repositories/
│   ├── test_incident_repository.py
│   └── ...
│
└── utils/
    └── test_prioritization_matrix.py
```

### 9.2 Интеграционные тесты (tests/integration/)

```
tests/integration/
├── test_incident_api.py
├── test_component_api.py
├── test_escalation_api.py
└── test_team_role_api.py
```

### 9.3 E2E тесты для ботов

```
tests/e2e/
├── test_slack_incident_commands.py
└── test_telegram_incident_commands.py
```

---

## 10. ПОРЯДОК РЕАЛИЗАЦИИ (MVP)

### Phase 1: База и API (неделя 1)

- [ ] 1.1 Создать миграции БД (все 9 таблиц)
- [ ] 1.2 Расширить models.py
- [ ] 1.3 Создать репозитории (5 новых)
- [ ] 1.4 Создать сервисы (5 сервисов)
- [ ] 1.5 Добавить API endpoints (6 групп)

### Phase 2: Админка (неделя 2)

- [ ] 2.1 Страница инцидентов (список + создание)
- [ ] 2.2 Просмотр инцидента с графом эскалации
- [ ] 2.3 Страница компонентов
- [ ] 2.4 Матрица приоритизации
- [ ] 2.5 Управление ролями в команде

### Phase 3: Конструктор эскалации (неделя 3)

- [ ] 3.1 UI builder для эскалации
- [ ] 3.2 Сохранение конфигурации
- [ ] 3.3 Предпросмотр графа
- [ ] 3.4 Тестирование конфигурации

### Phase 4: Боты (неделя 4)

- [ ] 4.1 Slack команды для инцидентов
- [ ] 4.2 Telegram команды для инцидентов
- [ ] 4.3 Отправка уведомлений об эскалации
- [ ] 4.4 Обработка ответов на эскалацию

### Phase 5: Автоматизация и таймеры (неделя 5)

- [ ] 5.1 Запуск первого шага эскалации при создании инцидента
- [ ] 5.2 Таймеры для шагов эскалации (APScheduler)
- [ ] 5.3 Автоматическая эскалация при timeout
- [ ] 5.4 Обработка timeout действий (write to chat, call, etc)

### Phase 6: Тестирование и доработки (неделя 6)

- [ ] 6.1 Unit тесты (сервисы и репозитории)
- [ ] 6.2 Интеграционные тесты (API)
- [ ] 6.3 E2E тесты (боты)
- [ ] 6.4 Баг фиксы и оптимизация

---

## 11. ПРИМЕЧАНИЯ

1. **Независимые таблицы**: TeamRole и TeamRoleMember полностью отдельны, не привязаны к Team в структуре, только через foreign key
2. **Гибкость ролей**: Каждая команда может определять свои роли (Dev-on-call, QA-on-call, Engineer, Lead и т.д.)
3. **Ротация**: Использует существующие RotationConfig и Schedule для определения кто сегодня на роли
4. **Эскалация**: Полностью конфигурируется через UI, сохраняется в JSON
5. **События**: Каждое изменение инцидента логируется в IncidentEvent для полного audit trail
6. **Статусы**: Четкие переходы между статусами с валидацией

---

## 12. ФАЙЛЫ ДЛЯ РЕДАКТИРОВАНИЯ

**Существующие файлы (расширение):**
- `app/models.py` — добавить 7 новых моделей, расширить Incident, Team, Workspace
- `app/main.py` — добавить новые роуты (incidents, components, etc)
- `app/handlers/slack_handler.py` — добавить команды
- `app/handlers/telegram_handler.py` — добавить команды
- `app/routes/admin/endpoints/` — новые endpoints

**Новые файлы:**
- `app/repositories/incident_repository.py`
- `app/repositories/component_repository.py`
- `app/repositories/team_role_repository.py`
- `app/repositories/escalation_config_repository.py`
- `app/repositories/prioritization_repository.py`
- `app/services/incident_service.py`
- `app/services/escalation_service.py`
- `app/services/team_role_service.py`
- `app/services/component_service.py`
- `app/services/prioritization_service.py`
- `app/routes/admin/endpoints/incidents.py`
- `app/routes/admin/endpoints/components.py`
- `app/routes/admin/endpoints/team_roles.py`
- `app/routes/admin/endpoints/escalation_configs.py`
- `app/routes/admin/endpoints/prioritization.py`
- `webapp/src/pages/incidents/IncidentsPage.tsx`
- `webapp/src/pages/incidents/IncidentDetailPage.tsx`
- `webapp/src/pages/components-list/ComponentsPage.tsx`
- `webapp/src/pages/settings/PrioritizationPage.tsx`
- `webapp/src/pages/settings/TeamsRolesPage.tsx`
- `webapp/src/pages/escalation/EscalationBuilderPage.tsx`
- `webapp/src/components/incidents/IncidentForm.tsx`
- `webapp/src/components/incidents/EscalationGraph.tsx`
- `webapp/src/components/escalation/EscalationBuilder.tsx`
- `webapp/src/services/incidentsApi.ts`
- `webapp/src/services/componentsApi.ts`
- `webapp/src/services/rolesApi.ts`
- `webapp/src/services/escalationApi.ts`
- `migrations/versions/` — 9 миграций Alembic

---

Это полный план, готовый к разработке?
