FROM python:3.11-slim

WORKDIR /app

# 1. Upgrade core pip tools first to fix the 'inspect' attribute error
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 2. Install your requirements
RUN pip install --no-cache-dir flask python-decouple ibm-watson-machine-learning nltk

# 3. Download NLTK data (this will now work)
RUN python -m nltk.downloader punkt punkt_tab

# Copy your code
COPY . .

CMD ["python", "app.py"]