FROM node:20-alpine AS frontend-builder

WORKDIR /webapp

# Copy webapp files
COPY webapp/package*.json ./
RUN npm install

COPY webapp .

# Build React app
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Copy built React app from frontend builder
COPY --from=frontend-builder /webapp/dist ./webapp/dist

# Run the app
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
