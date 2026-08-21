# Small production-ready image for the RxVerify Flask application.
# Multi-stage build for smaller final image
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
# Install packages system-wide (not --user) so they're available to all users
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user first
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder (system-wide install)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app.py ./
COPY config.py ./
COPY src ./src
COPY templates ./templates
COPY static ./static

# The SQLite database lives here. Docker Compose mounts a named volume at this path.
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
