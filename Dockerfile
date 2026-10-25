# Use official lightweight Python runtime
FROM python:3.11-slim

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
COPY . .

# Drop privileges to non-root user
USER appuser

# Expose default Cloud Run port
EXPOSE 8080

# Run uvicorn server binding to dynamic Cloud Run $PORT (defaults to 8080)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
