# VeriQuest / Fake News Detection — Render Docker image
# Includes Tesseract OCR for image verification

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app

# System deps: Tesseract OCR + build tools for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir Pillow pytesseract trafilatura beautifulsoup4 lxml newspaper3k

# App code
COPY . .

# Confirm tesseract is available at build time
RUN tesseract --version && python -c "import pytesseract; print('pytesseract OK', pytesseract.get_tesseract_version())"

EXPOSE 10000

# Same as Procfile
CMD gunicorn -w 2 -b 0.0.0.0:${PORT} webapp.app:app
