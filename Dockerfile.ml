FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app
USER app

# Health check endpoint using simple HTTP server
CMD ["python", "-c", "
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    model_type = os.getenv('MODEL_TYPE', 'unknown')
    return jsonify({'status': 'healthy', 'model_type': model_type})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
"]
