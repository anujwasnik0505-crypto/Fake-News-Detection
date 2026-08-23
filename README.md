# Fake News Detection — Full Project

Headline-level fake news classifier combining **5 classical ML models + 2 deep learning
models**, live cross-source verification, a professional fact-checker database lookup,
rule-based red-flag detection, an optional LLM reasoning layer, a local history database,
**Explainable AI (LIME + SHAP)** word-level evidence, and an in-app **chatbot** ("Ask the
Desk") for discussing results and how the system works.

## Models
- **Classical ML (TF-IDF features):** Logistic Regression, Naive Bayes, Linear SVM, Random Forest, Decision Tree
- **Deep Learning (Keras):** BiLSTM, Text-CNN

## The 5-layer verdict pipeline
Every headline check runs through these layers in order — each is skipped automatically
if its API key isn't configured, so the project always works even with zero keys set
(using free fallbacks):

1. **Live verification** — NewsAPI.org (or free Google News RSS fallback) checks if a
   trusted outlet is currently reporting the headline → `REAL — Verified`
2. **Fact-check database** — Google Fact Check Tools API checks if professional
   fact-checkers (PolitiFact, Alt News, Snopes, etc.) have already reviewed this claim
3. **Red-flag pattern check** — rule-based detection of common fake-news phrasing
   ("all citizens", "banned starting tomorrow", "no application needed", etc.)
4. **LLM reasoning** — Claude API judges plausibility using general world knowledge,
   catching implausible claims that don't match any hardcoded pattern
5. **Trained model fallback** — the best-performing ML/DL model's style-based prediction,
   used only if nothing above reached a verdict

Every check (whichever layer decided it) is logged to a local SQLite database (`history.db`).

## Setup

```bash
pip install -r requirements.txt
```

### 1. Get the dataset
Download the **"Fake and Real News Dataset"** from Kaggle:
https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset

Place `Fake.csv` and `True.csv` inside the `data/` folder.

### 2. (Optional) Add API keys
Copy `.env.example` to `.env` and fill in any keys you have:
```
NEWSAPI_KEY=...              # https://newsapi.org/register (free, 100 req/day)
GOOGLE_FACTCHECK_API_KEY=... # https://console.cloud.google.com (free)
GEMINI_API_KEY=...           # https://aistudio.google.com/apikey (free, 1500 req/day)
ANTHROPIC_API_KEY=...        # https://console.anthropic.com (free trial credits, then paid)
```
Every key is optional — leaving any blank just skips that layer and falls back to the
next one. With zero keys set, the project still runs fully using free RSS + rule-based
checks + the trained model. For the LLM layer, set GEMINI_API_KEY (free) — it is tried
before ANTHROPIC_API_KEY, so you never need both.

### 3. Train the models
```bash
python main.py
```
Trains all 7 models, evaluates them, and picks the best one automatically
(`outputs/best_model.json`). Takes 5-15 minutes (mostly the DL models).

Re-run later without retraining:
```bash
python main.py --skip-train
```

### 4. Check headlines (CLI)
```bash
python check_headline.py                    # interactive mode
python check_headline.py --text "..."        # single headline
python check_headline.py --history            # view past checks
```

### 5. Web UI
```bash
python webapp/app.py
```
Open **http://127.0.0.1:5000** — submit headlines, see the live feed, and view your
check history, all in the browser.

### 6. Explainable AI (LIME + SHAP)
On the web UI, after an **unverified** (model-fallback) result, a "WHY? - SHOW EVIDENCE"
button appears. Clicking it highlights the words in the headline that pushed the model's
prediction toward REAL (green) or FAKE (red) - switch between LIME and SHAP methods with
the toggle. This only applies to layer-5 (model) verdicts, since layers 1-4 aren't driven
by the model's word weights.

- **LIME** perturbs the headline (removing/shuffling words) and fits a local model to see
  which words mattered most - fast, works for any model type.
- **SHAP** uses Shapley values (game theory) to attribute the prediction to each word more
  rigorously, at the cost of being slightly slower.

### 7. Chatbot ("Ask the Desk")
A floating chat button on the web UI opens a conversational assistant (same LLM provider
as the reasoning layer - Gemini or Claude) that can explain a result, describe how the
5-layer pipeline works, or discuss media literacy generally. Needs GEMINI_API_KEY or
ANTHROPIC_API_KEY set; without one, the chat explains it needs a key rather than failing
silently.

### 8. API (no UI, JSON only)
```bash
python api.py
```
Endpoints: `POST /check`, `GET /live-feed`, `GET /history`, `GET /stats`

```bash
curl -X POST http://127.0.0.1:5000/check -H "Content-Type: application/json" -d "{\"headline\": \"Some headline\"}"
```

## GPU
TensorFlow automatically uses a GPU if one is available and properly configured (CUDA +
cuDNN) — no code changes needed. This project's headline-classification task is small
enough that CPU training (5-15 min) is perfectly fine; a GPU mainly helps for much larger
models or datasets. To check what's detected on your machine:
```bash
python -m src.gpu_utils
```

## Database
Every check is logged to `history.db` (SQLite, created automatically, git-ignored).
No setup needed — `src/database.py` handles table creation on first use. Query it
directly with any SQLite browser, or via `check_headline.py --history` /
the `/history` and `/stats` API endpoints.

## Deploying with a custom domain
To make the web UI or API publicly accessible with your own domain (e.g.
`yourproject.com`) instead of `127.0.0.1`:
1. Deploy the app to a host (e.g. Render, Railway — free tiers available; see the
   `Procfile` in this repo, already configured for `gunicorn`)
2. Buy a domain from a registrar (Namecheap, GoDaddy, Hostinger — roughly ₹500-1500/year)
3. Point the domain's DNS (a CNAME or A record) to your host's provided URL — each
   host's dashboard has a "Custom Domain" section with exact instructions
This is an infrastructure/hosting step, not a code change — the app itself doesn't
need to know its own domain name.

## Project structure
```
fake_news_project/
  data/, models/, outputs/
  src/
    preprocess.py           # text cleaning
    utils.py                 # data loading, train/test split
    train_ml_models.py       # 5 classical ML models
    train_dl_models.py       # BiLSTM + Text-CNN
    evaluate.py               # metrics, charts, best model selection
    realtime_news.py          # RSS fetch + REAL/FAKE prediction
    verify_news.py            # live cross-source verification (NewsAPI + RSS)
    factcheck.py               # Google Fact Check Tools API
    plausibility_check.py      # rule-based red-flag detection
    llm_analysis.py             # Gemini/Claude plausibility reasoning
    gpu_utils.py                 # GPU detection/reporting
    database.py                   # SQLite check history logging
    explain.py                    # LIME + SHAP word-level explanations
    chatbot.py                     # "Ask the Desk" LLM chat assistant
  webapp/
    app.py                    # Flask backend for the browser UI
    templates/index.html, static/style.css, static/script.js
  main.py
  check_headline.py           # CLI hybrid headline checker
  api.py                       # JSON-only REST API
  .env.example
  requirements.txt
```

## Notes / caveats (worth mentioning in your report)
- The Kaggle dataset has a known **source bias**: most "real" headlines come from Reuters
  and most "fake" ones from other outlets, so the trained model alone can misjudge
  current headlines with unfamiliar vocabulary — this is exactly why the verification,
  fact-check, red-flag, and LLM layers exist ahead of the model in the pipeline.
- Headlines are short, so classical TF-IDF models (esp. Linear SVM, Logistic Regression)
  often perform comparably to the DL models — the evaluation report shows this directly.
