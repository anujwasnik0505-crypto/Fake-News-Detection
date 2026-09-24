# Image OCR fix on Render — use Docker

## Why Aptfile failed

Render **Native** Python services cannot install system packages like
`tesseract-ocr` with apt-get. Aptfile often does nothing on native runtimes.

Official fix from Render support: **Docker**.

## What to add in repo root

1. `Dockerfile` (provided)
2. Update `requirements.txt` — add at the end:

```
Pillow
pytesseract
trafilatura
beautifulsoup4
lxml
newspaper3k
```

## Git push

```bash
git add Dockerfile requirements.txt
git commit -m "Docker + Tesseract for image OCR on Render"
git push origin main
```

## Render dashboard settings

1. Open your Web Service
2. **Settings → Build & Deploy**
3. **Environment** / **Runtime**: change to **Docker**
   (or create new service with "Docker" environment)
4. Dockerfile Path: `./Dockerfile` (default)
5. Save → **Manual Deploy**

Build will run `apt-get install tesseract-ocr` inside the image.
Takes ~5–15 minutes first time.

## Test

After Live:
- Site → Image tab → upload screenshot → Verify
- Error "tesseract is not installed" should be gone

## If Docker option not visible

Create a **new** Web Service:
- Connect same GitHub repo
- Environment: **Docker**
- Instance: Free
- Add same env vars (GEMINI_API_KEY etc.) from old service
- Deploy, then point custom domain / use new URL
