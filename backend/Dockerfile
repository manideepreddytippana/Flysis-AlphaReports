FROM python:3.10-slim

WORKDIR /app

# Installs system dependencies
RUN apt-get update && apt-get install -y \
    ghostscript \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Installs python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copies entire app code
COPY . .

# cmd to run FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
