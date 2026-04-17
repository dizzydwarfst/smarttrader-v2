# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Install deps first (cached layer).
# We use `npm install` rather than `npm ci` because the lock file can drift
# when deps are updated locally; this keeps the Docker build resilient.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund --loglevel=error

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
