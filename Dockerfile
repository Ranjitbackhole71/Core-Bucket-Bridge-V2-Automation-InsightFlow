# Dockerfile - lightweight FastAPI server for inference
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app

# Expose port and start uvicorn
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]