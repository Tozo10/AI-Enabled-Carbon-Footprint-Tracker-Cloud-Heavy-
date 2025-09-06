# ---- Stage 1: Build Stage ----
# Use an official Python runtime as a parent image
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# ---- Stage 2: Final Stage ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy project code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the application using Gunicorn
# This command starts the Gunicorn server and points it to your project's wsgi file.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]