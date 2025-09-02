FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy code
COPY backend backend
COPY frontend frontend

# Gunicorn will bind to $PORT provided by Bolt
ENV PORT=8000
EXPOSE 8000

# Start Flask app from backend using gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000", "--chdir", "backend"]