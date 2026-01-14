# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client library (runtime dependency)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app.py .
COPY models.py .
COPY bakery_inventory.py .
COPY templates/ templates/
COPY static/ static/

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose port (Cloud Run uses PORT env variable)
EXPOSE 8080
ENV PORT=8080

# Run with gunicorn
# Using --timeout 0 for Cloud Run (it handles request timeouts)
# 2 workers and 4 threads is good for 4-5 concurrent users
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 0 app:app
