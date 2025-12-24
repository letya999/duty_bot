# Duty Bot Admin API - Полная документация

## 📚 Введение

Duty Bot Admin API предоставляет полный REST API для управления дежурствами, командами и эскалациями. API использует Bearer token аутентификацию и возвращает JSON responses.

## 🔐 Аутентификация

### Получение токена

Все запросы к защищенным endpoints требуют Bearer token. Получите токен через endpoint `/api/admin/auth/token`:

```bash
curl -X POST "http://localhost:8000/api/admin/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
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

### Использование токена

Добавьте токен в заголовок `Authorization` всех запросов:

```bash
curl -X GET "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 📖 Доступная документация

### Swagger UI (интерактивная)
- **URL**: `http://localhost:8000/api/docs`
- Можно тестировать endpoints прямо в браузере
- Включает авторизацию через OAuth2

### ReDoc (красивая документация)
- **URL**: `http://localhost:8000/api/redoc`
- Удобный формат для чтения

### OpenAPI Schema (JSON)
- **URL**: `http://localhost:8000/api/openapi.json`
- Полная схема в формате OpenAPI 3.0

## 🎯 Основные endpoint группы

### 1. Authentication (Аутентификация)
- `POST /api/admin/auth/token` - Получить Bearer токен
- `POST /api/admin/auth/token/validate` - Проверить валидность токена

### 2. Users (Пользователи)
- `GET /api/admin/user/info` - Получить информацию о текущем пользователе
- `GET /api/admin/users` - Список всех пользователей

### 3. Teams (Команды) - Полный CRUD
- `GET /api/admin/teams` - Список всех команд
- `POST /api/admin/teams` - Создать новую команду
- `PUT /api/admin/teams/{team_id}` - Обновить команду
- `DELETE /api/admin/teams/{team_id}` - Удалить команду
- `POST /api/admin/teams/{team_id}/members` - Добавить члена команды
- `DELETE /api/admin/teams/{team_id}/members/{member_id}` - Удалить члена команды

### 4. Schedules (Дежурства) - Управление графиком
- `GET /api/admin/schedule/month?year=2024&month=12` - График на месяц
- `GET /api/admin/schedule/day/{date}` - График на день
- `GET /api/admin/schedules/range?start_date=2024-12-01&end_date=2024-12-31` - За период
- `POST /api/admin/schedule/assign` - Назначить дежурство
- `POST /api/admin/schedule/assign-bulk` - Массовое назначение
- `PUT /api/admin/schedule/{schedule_id}` - Обновить дежурство
- `PATCH /api/admin/schedule/{schedule_id}/move` - Перенести на другую дату
- `PATCH /api/admin/schedule/{schedule_id}/replace` - Заменить человека
- `DELETE /api/admin/schedule/{schedule_id}` - Удалить дежурство

### 4b. Shifts (Смены) - Управление сменами для команд с has_shifts=true
- `POST /api/admin/shifts/assign` - Добавить пользователя на смену
- `POST /api/admin/shifts/assign-bulk` - Массовое добавление в смены на диапазон дат
- `GET /api/admin/shifts/date/{date}?team_id={id}` - Получить смены на дату
- `GET /api/admin/shifts/range?start_date=2024-12-01&end_date=2024-12-31` - Получить смены за период
- `DELETE /api/admin/shifts/{shift_id}` - Удалить смену целиком
- `DELETE /api/admin/shifts/{shift_id}/members/{user_id}` - Удалить пользователя из смены

### 5. Escalations (Эскалации) - CTO управление
- `GET /api/admin/escalations` - Список всех эскалаций
- `POST /api/admin/escalations` - Создать эскалацию
- `DELETE /api/admin/escalations/{escalation_id}` - Удалить эскалацию

### 6. Admin (Администрирование)
- `GET /api/admin/admins` - Список администраторов
- `POST /api/admin/users/{user_id}/promote` - Повысить до админа
- `POST /api/admin/users/{user_id}/demote` - Удалить права админа
- `GET /api/admin/admin-logs` - Логи всех действий администраторов

### 7. Statistics (Статистика)
- `GET /api/admin/stats/schedules` - Статистика по дежурствам

## 📋 Примеры использования

### Пример 1: Получение токена и списка пользователей

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST "http://localhost:8000/api/admin/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# 2. Получить пользователей
curl -X GET "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer $TOKEN"
```

### Пример 2: Создание команды и добавление членов

```bash
# Создать команду
curl -X POST "http://localhost:8000/api/admin/teams" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend-team",
    "display_name": "Backend Team",
    "has_shifts": false,
    "team_lead_id": 1
  }'

# Добавить члена команды (ID команды и пользователя)
curl -X POST "http://localhost:8000/api/admin/teams/1/members" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'
```

### Пример 3: Назначить дежурство

```bash
# Одного человека на один день
curl -X POST "http://localhost:8000/api/admin/schedule/assign" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "duty_date": "2024-12-25",
    "team_id": 1
  }'

# Массовое назначение - несколько человек на диапазон дат
curl -X POST "http://localhost:8000/api/admin/schedule/assign-bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [1, 2, 3],
    "start_date": "2024-12-25",
    "end_date": "2024-12-31",
    "team_id": 1
  }'
```

### Пример 3b: Работа со сменами (для команд с has_shifts=true)

```bash
# Добавить одного человека на смену
curl -X POST "http://localhost:8000/api/admin/shifts/assign" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "shift_date": "2024-12-25",
    "team_id": 1
  }'

# Добавить нескольких человек на смены (диапазон дат)
# Все указанные пользователи будут добавлены на каждый день в диапазоне
curl -X POST "http://localhost:8000/api/admin/shifts/assign-bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [5, 7, 8],
    "start_date": "2024-12-25",
    "end_date": "2024-12-31",
    "team_id": 1
  }'

# Получить все смены на конкретную дату
curl -X GET "http://localhost:8000/api/admin/shifts/date/2024-12-25?team_id=1" \
  -H "Authorization: Bearer $TOKEN"

# Удалить пользователя из смены
curl -X DELETE "http://localhost:8000/api/admin/shifts/1/members/5" \
  -H "Authorization: Bearer $TOKEN"

# Удалить смену целиком
curl -X DELETE "http://localhost:8000/api/admin/shifts/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Пример 4: Обновить дежурство (перенести или заменить)

```bash
# Перенести дежурство на другую дату
curl -X PATCH "http://localhost:8000/api/admin/schedule/1/move" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_date": "2024-12-26"}'

# Заменить человека на дежурстве
curl -X PATCH "http://localhost:8000/api/admin/schedule/1/replace" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 10}'
```

### Пример 5: Управление эскалациями (CTO)

```bash
# Назначить CTO команде
curl -X POST "http://localhost:8000/api/admin/escalations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 1,
    "cto_id": 5
  }'

# Установить глобального CTO
curl -X POST "http://localhost:8000/api/admin/escalations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cto_id": 10
  }'

# Получить все эскалации
curl -X GET "http://localhost:8000/api/admin/escalations" \
  -H "Authorization: Bearer $TOKEN"
```

## 🔧 Структура данных

### User
```json
{
  "id": 1,
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "is_admin": true,
  "workspace_id": 1,
  "telegram_username": "johndoe",
  "slack_user_id": "U123456"
}
```

### Team
```json
{
  "id": 1,
  "name": "backend-team",
  "display_name": "Backend Team",
  "has_shifts": false,
  "workspace_id": 1,
  "members": [
    {"id": 1, "first_name": "John", ...}
  ],
  "description": "Backend development team"
}
```

### Schedule (для команд без смен, has_shifts=false)
```json
{
  "id": 1,
  "user_id": 5,
  "duty_date": "2024-12-25",
  "team_id": 1,
  "user": {"id": 5, "first_name": "Ivan"},
  "team": {"id": 1, "name": "backend-team"}
}
```

### Shift (для команд со сменами, has_shifts=true)
```json
{
  "id": 1,
  "date": "2024-12-25",
  "team_id": 1,
  "team": {"id": 1, "name": "backend-team"},
  "users": [
    {"id": 5, "first_name": "Ivan"},
    {"id": 7, "first_name": "Maria"},
    {"id": 8, "first_name": "Alexey"}
  ]
}
```

### Escalation
```json
{
  "id": 1,
  "team_id": 1,
  "cto_id": 10,
  "team": {"id": 1, "name": "backend-team"},
  "cto_user": {"id": 10, "first_name": "Chief"}
}
```

## ⚠️ Коды ошибок

| Код | Описание | Пример |
|-----|---------|--------|
| 200 | OK | Успешный запрос |
| 400 | Bad Request | Неверные параметры |
| 401 | Unauthorized | Токен отсутствует или истек |
| 403 | Forbidden | Недостаточно прав (требуется админ) |
| 404 | Not Found | Ресурс не найден |
| 500 | Server Error | Ошибка сервера |

## 🔒 Требования безопасности

- Все endpoints (кроме `/auth/token`) требуют валидный Bearer token
- Большинство endpoints требуют права администратора (`is_admin=true`)
- Токены истекают через 24 часа
- Используйте HTTPS в production

## 🚀 Интеграция

### JavaScript/TypeScript
```javascript
const apiClient = {
  async request(method, endpoint, data) {
    const token = localStorage.getItem('token');
    return fetch(`http://localhost:8000/api/admin${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: data ? JSON.stringify(data) : null
    }).then(r => r.json());
  },

  // Примеры методов
  getUsers: () => this.request('GET', '/users'),
  getTeams: () => this.request('GET', '/teams'),
  assignDuty: (data) => this.request('POST', '/schedule/assign', data)
};
```

### Python
```python
import requests

class DutyBotAPI:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token

    def get_token(self, username, password):
        r = requests.post(
            f"{self.base_url}/api/admin/auth/token",
            json={"username": username, "password": password}
        )
        return r.json()['access_token']

    def _request(self, method, endpoint, data=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        url = f"{self.base_url}/api/admin{endpoint}"
        return requests.request(method, url, json=data, headers=headers).json()

    def get_users(self):
        return self._request('GET', '/users')

    def assign_duty(self, user_id, duty_date, team_id=None):
        return self._request('POST', '/schedule/assign', {
            'user_id': user_id,
            'duty_date': duty_date,
            'team_id': team_id
        })

# Использование
api = DutyBotAPI()
api.token = api.get_token('admin', 'admin')
users = api.get_users()
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте токен через `/auth/token/validate`
2. Убедитесь в наличии прав администратора
3. Проверьте логи сервера
4. Обратитесь в поддержку на email: support@dutybot.dev

## 📝 Версия

- API Version: 1.0.0
- Last Updated: 2024-12-25
