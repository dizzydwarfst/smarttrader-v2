# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Install deps first (cached layer)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

# Copy sources and build
COPY frontend/ ./
RUN npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
# (frontend/ source is excluded by .dockerignore; we inject the build below)
COPY . .

# Drop in the compiled React app — api.py serves it from frontend/build
COPY --from=frontend-build /frontend/build ./frontend/build

EXPOSE 8000

CMD ["python", "bot.py"]
