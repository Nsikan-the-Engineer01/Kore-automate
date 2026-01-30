FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create wheels from requirements
COPY ./requirements/base.txt ./requirements/production.txt ./

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r base.txt && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r production.txt

# Final stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r django && \
    useradd -r -g django django && \
    mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R django:django /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install Python dependencies from wheels
RUN pip install --no-cache /wheels/*

# Copy project source
COPY --chown=django:django . /app

# Collect static files at runtime
RUN python manage.py collectstatic --noinput --clear || true

# Ensure ownership is correct for all app files (including logs)
RUN chown -R django:django /app || true

# Switch to non-root user
USER django

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Expose port
EXPOSE 8000

# Entrypoint
CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]

