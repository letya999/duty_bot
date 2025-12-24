FROM node:20-alpine

WORKDIR /app

# Копируем файлы зависимостей
COPY package*.json ./

# Устанавливаем ВСЕ зависимости (включая devDependencies для vite)
RUN npm install

# Копируем исходный код
COPY . .

# Открываем порт
EXPOSE 5173

# По умолчанию запускаем сервер разработки
# (В docker-compose это можно переопределить)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
