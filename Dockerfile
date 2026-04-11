FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Dashboard port
EXPOSE 8000

# Run bot (dashboard auto-starts with it)
CMD ["python", "bot.py"]
