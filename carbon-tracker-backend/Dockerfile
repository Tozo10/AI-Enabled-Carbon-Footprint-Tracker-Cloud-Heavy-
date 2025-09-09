# ---- Stage 1: Build Stage ----
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Stage 2: Final Stage ----
FROM python:3.11-slim-bookworm

WORKDIR /app

# Create a non-root user and group
RUN addgroup --system app && adduser --system --ingroup app appuser

# Copy installed dependencies
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir /wheels/*

# Copy project code and change ownership
COPY . .
RUN chown -R appuser:app /app

# Switch to the non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "core.wsgi:application"]