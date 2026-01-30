FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN pip install flask python-decouple ibm-watson-machine-learning nltk

# Download NLTK data
RUN python -m nltk.downloader punkt punkt_tab

# Copy your code
COPY . .

CMD ["python", "app.py"]