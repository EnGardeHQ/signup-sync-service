FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx, os; httpx.get(f'http://localhost:{os.getenv(\"PORT\", \"8001\")}/health')"

# Run application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
