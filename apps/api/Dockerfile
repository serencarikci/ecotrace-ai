# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin ecotrace

COPY pyproject.toml ./
COPY VERSION ./
COPY src ./src
COPY alembic.ini ./
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
      "fastapi>=0.115.0" \
      "uvicorn[standard]>=0.32.0" \
      "pydantic[email]>=2.9.0" \
      "pydantic-settings>=2.6.0" \
      "sqlalchemy>=2.0.36" \
      "alembic>=1.14.0" \
      "psycopg[binary]>=3.2.0" \
      "PyJWT[crypto]>=2.9.0" \
      "pwdlib[argon2]>=0.2.0" \
      "python-multipart>=0.0.12" \
      "structlog>=24.4.0" \
      "httpx>=0.27.0" \
    && mkdir -p /data/attachments \
    && chown -R ecotrace:ecotrace /app /data/attachments \
    && chmod +x /app/docker-entrypoint.sh

# Entrypoint starts as root to fix volume ownership, then drops to ecotrace.
USER root

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "ecotrace.main:app", "--host", "0.0.0.0", "--port", "8000"]
