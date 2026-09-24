# Image OCR setup (Render / VPS)

Error: **Tesseract binary not found** means the server can run Python
but does not have the system OCR program installed.

## Option A — Render.com (recommended)

1. Put this file in the **repo root** (same level as `requirements.txt`):

   **Aptfile**
   ```
   tesseract-ocr
   tesseract-ocr-eng
   tesseract-ocr-hin
   libtesseract-dev
   libgl1
   libglib2.0-0
   ```

2. In `requirements.txt` (or requirements-phase2-3.txt) ensure:
   ```
   Pillow
   pytesseract
   trafilatura
   beautifulsoup4
   lxml
   newspaper3k
   ```

3. Commit + push → Render will auto-redeploy and install apt packages.

4. After deploy, open site → Image tab → try again.

## Option B — Ubuntu VPS

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin
pip install Pillow pytesseract
# restart gunicorn / flask
```

## Option C — Without OCR

Use **Headline** or **URL** tabs — image check needs Tesseract.

## Verify on server

```bash
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```
