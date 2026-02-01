# ---- Stage 1: Build Stage ----
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates

# 1. UPGRADE PIP & INSTALL BUILD TOOLS
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# 2. Install Python dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Stage 2: Final Stage ----
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install ca-certificates (needed for SSL/NLTK downloads and IBM API calls)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN addgroup --system app && adduser --system --ingroup app appuser

# Copy installed dependencies
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# 3. UPGRADE PIP & INSTALL PACKAGES
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir /wheels/*

# --- NEW: DOWNLOAD NLTK DATA ---
# Set the data path and ensure the directory exists with proper permissions
ENV NLTK_DATA=/usr/share/nltk_data
RUN mkdir -p $NLTK_DATA && chown -R appuser:app $NLTK_DATA

# Robust NLTK download script:
# 1. It handles SSL certificate verification issues (common in college/corporate networks).
# 2. It uses python -c to avoid interactive prompts that cause EOFErrors.
RUN python -c "import nltk; import ssl; \
try: \
    _create_unverified_https_context = ssl._create_unverified_context; \
except AttributeError: \
    pass; \
else: \
    ssl._create_default_https_context = _create_unverified_https_context; \
nltk.download('punkt', download_dir='$NLTK_DATA'); \
nltk.download('punkt_tab', download_dir='$NLTK_DATA')"
# -------------------------------

# Copy project code and change ownership
COPY . .
RUN chown -R appuser:app /app

# Switch to the non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 --workers 4 core.wsgi:application"]