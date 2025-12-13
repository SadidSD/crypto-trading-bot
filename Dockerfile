FROM python:3.11-slim

# Install system dependencies (including Redis)
RUN apt-get update && apt-get install -y \
    gcc \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the port (informative only, Railway handles mapping)
EXPOSE 8080

# STARTUP COMMAND:
# 1. Start Redis in background
# 2. Start Python Server (which connects to local Redis)
CMD redis-server --daemonize yes && python server.py
