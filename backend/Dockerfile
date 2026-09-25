FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for PDF parsing (Camelot, OpenCV, PyMuPDF, etc.)
RUN apt-get update && apt-get install -y \
    ghostscript \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
