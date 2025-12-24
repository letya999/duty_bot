# OAuth Setup Guide для Web Admin Panel

Этот документ описывает необходимые настройки для работы OAuth аутентификации в web admin panel.

## Telegram OAuth

### Вариант 1: Telegram Mini App (Рекомендуется)

Для Telegram используется встроенная валидация init data через бот токен. Это наиболее простой и безопасный способ.

**Требования:**
1. Telegram Bot Token (уже должен быть в `.env`)
2. Web App должен быть открыт из Telegram Mini App контекста

**Настройка бота:**
```bash
# В BotFather команда /setmenubutton для вашего бота
# Установите Web App с URL вашего приложения
# Пример: https://yourdomain.com/web/auth/login
```

**Переменные окружения:**
```env
TELEGRAM_TOKEN=ваш_token_здесь
```

**Как работает:**
- Пользователь открывает ваше приложение через Telegram Mini App
- Web App получает `initData` с данными пользователя и подписью
- Сервер валидирует подпись используя HMAC-SHA256 с bot token
- При успешной валидации пользователь получает сессию

**Тестирование локально:**
```bash
# Используйте Telegram Web App Demo или создайте простой тест скрипт
# который генерирует корректный initData для тестирования
```

---

## Slack OAuth

### Обязательная настройка

**Шаг 1: Создайте Slack App**

1. Перейдите на https://api.slack.com/apps
2. Нажмите "Create New App" → "From scratch"
3. Назовите приложение: "Duty Bot Admin"
4. Выберите workspace

**Шаг 2: Настройте OAuth Redirect URLs**

1. В левом меню: "OAuth & Permissions"
2. В секции "Redirect URLs" нажмите "Add New Redirect URL"
3. Добавьте: `https://yourdomain.com/web/auth/slack-callback`
   - Для локального тестирования используйте: `http://localhost:8000/web/auth/slack-callback`
4. Нажмите "Save URLs"

**Шаг 3: Установите требуемые Scopes**

В той же странице "OAuth & Permissions" найдите "Scopes":

**Bot Token Scopes:**
- `chat:write` - отправка сообщений
- `users:read` - чтение информации о пользователях
- `users:read.email` - чтение email пользователей
- `team:read` - чтение информации о workspace

**User Token Scopes:**
- `users:read`
- `users:read.email`

**Шаг 4: ПолучитеCredentails**

1. В разделе "OAuth Tokens & Installing Working Spaces":
   - Нажмите "Install to Workspace"
   - Разрешите доступ
2. Скопируйте значения:
   - **Client ID** - из разделов "App Credentials"
   - **Client Secret** - из разделов "App Credentials"
   - **Bot User OAuth Token** (начинается с `xoxb-`) - сохраните как `SLACK_BOT_TOKEN`

**Шаг 5: Добавьте в .env**

```env
# Slack Bot (для отправки сообщений)
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C123456789

# Slack OAuth (для веб-панели)
SLACK_CLIENT_ID=123456789.1234567890123
SLACK_CLIENT_SECRET=your-client-secret-here
SLACK_REDIRECT_URI=https://yourdomain.com/web/auth/slack-callback
```

**Шаг 6: Получите Signing Secret**

1. В левом меню: "Basic Information"
2. Найдите "App Credentials"
3. Скопируйте "Signing Secret" → `SLACK_SIGNING_SECRET`

---

## Переменные окружения (.env)

### Полный пример конфигурации:

```env
# === DATABASE ===
DATABASE_URL=postgresql+asyncpg://user:password@localhost/duty_bot

# === TELEGRAM ===
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789

# === SLACK ===
# Bot токены
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CHANNEL_ID=C123456789

# OAuth для веб-панели
SLACK_CLIENT_ID=123456789.1234567890123
SLACK_CLIENT_SECRET=your-client-secret-here
SLACK_REDIRECT_URI=https://yourdomain.com/web/auth/slack-callback

# === APPLICATION ===
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
TIMEZONE=UTC
MORNING_DIGEST_TIME=09:00

# === ADMIN SETTINGS ===
ADMIN_TELEGRAM_IDS=123456789,987654321
ADMIN_SLACK_IDS=U123456789,U987654321
```

---

## Тестирование

### Тестирование Telegram

```bash
# Создайте простой тест скрипт для генерации валидного initData
# или используйте Telegram Web App в development mode

# Сервер должен запуститься на:
http://localhost:8000/web/auth/login

# Или через mini app:
https://t.me/YourBotName/app
```

### Тестирование Slack

```bash
# 1. Откройте браузер и перейдите на:
http://localhost:8000/web/auth/slack-login

# 2. Вас перенаправит на Slack для авторизации

# 3. После разрешения вас перенаправит на:
http://localhost:8000/web/auth/slack-callback?code=...&state=...

# 4. Затем перенаправит на dashboard
http://localhost:8000/web/dashboard
```

---

## Решение проблем

### Ошибка: "Invalid Telegram signature"

- Проверьте, что `TELEGRAM_TOKEN` правильно скопирован
- Убедитесь, что приложение открыто в контексте Telegram Mini App
- Проверьте, что время на сервере синхронизировано (используется validation с auth_date)

### Ошибка: "Invalid state" при Slack OAuth

- Убедитесь, что `SLACK_REDIRECT_URI` совпадает с URL в Slack App Settings
- Проверьте, что браузер поддерживает cookies (нужны для CSRF protection)

### Ошибка: "Redirect URI mismatch"

- Зайдите в Slack App Settings → OAuth & Permissions
- Убедитесь, что `SLACK_REDIRECT_URI` точно совпадает (включая протокол и путь)

### Создание пользователя не работает

- Проверьте, что база данных работает и миграции применены
- Убедитесь, что таблица `users` существует
- Проверьте логи сервера на ошибки подключения к БД

---

## Развертывание в Production

При развертывании на боевой сервер:

1. **Обновите REDIRECT_URI:**
   ```env
   SLACK_REDIRECT_URI=https://yourdomain.com/web/auth/slack-callback
   ```

2. **Обновите Slack App Settings:**
   - OAuth & Permissions → Redirect URLs
   - Добавьте новый URL production сервера

3. **Используйте HTTPS:**
   - OAuth требует HTTPS в production
   - Настройте SSL сертификаты

4. **Установите JWT или другой механизм сессий:**
   - Текущий механизм (in-memory) подходит для разработки
   - Для production используйте Redis или БД для хранения сессий

---

## API для управления административными правами

После входа админ может управлять другими пользователями через API:

```bash
# Сделать пользователя админом
POST /api/miniapp/users/{user_id}/promote

# Убрать права админа
POST /api/miniapp/users/{user_id}/demote

# Получить список админов
GET /api/miniapp/admins
```

Эти endpoints должны быть добавлены в `app/routes/miniapp.py` для полной функциональности.
