FROM python:3.11-slim

# System deps for `unstructured` PDF parsing (poppler = PDF -> text, tesseract = OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr libmagic1 libgl1 build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]
