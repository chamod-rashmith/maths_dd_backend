# Use official lightweight Python runtime
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory inside container
WORKDIR /app

# Create non-root system user for container security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Install dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY --chown=appuser:appgroup . .

# Drop privileges to non-root user
USER appuser

# Expose default Cloud Run port
EXPOSE 8080

# Run alembic migrations then launch uvicorn server binding to dynamic Cloud Run $PORT (defaults to 8080)
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
