"""Fetch live news headlines (RSS, no API key needed) and classify them."""
import joblib
import feedparser
from src.preprocess import clean_text
# NOTE: tensorflow (via src.train_dl_models) is imported lazily below, only when
# a DL model is actually selected — this keeps memory usage low on hosts with
# limited RAM (e.g. free-tier deployments) when an ML model is used instead.

# Free public RSS feeds — no API key required
DEFAULT_FEEDS = {
    "Google News (Top Stories)": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
}


def fetch_live_headlines(feed_url=None, limit=15):
    """Pull latest headlines from an RSS feed. Defaults to Google News top stories."""
    url = feed_url or DEFAULT_FEEDS["Google News (Top Stories)"]
    feed = feedparser.parse(url)
    headlines = [entry.title for entry in feed.entries[:limit]]
    if not headlines:
        raise RuntimeError(f"No headlines fetched from {url}. Check network / feed URL.")
    return headlines


def load_best_model(model_name, models_dir):
    """Load whichever model type won evaluation (ML joblib or DL keras)."""
    import os
    ml_path = os.path.join(models_dir, f"{model_name}.joblib")
    dl_path = os.path.join(models_dir, f"{model_name}.keras")

    if os.path.exists(ml_path):
        model = joblib.load(ml_path)
        vectorizer = joblib.load(os.path.join(models_dir, "tfidf_vectorizer.joblib"))
        return {"type": "ml", "model": model, "vectorizer": vectorizer}
    elif os.path.exists(dl_path):
        from tensorflow.keras.models import load_model
        import pickle
        model = load_model(dl_path)
        with open(os.path.join(models_dir, "tokenizer.pkl"), "rb") as f:
            tokenizer = pickle.load(f)
        return {"type": "dl", "model": model, "tokenizer": tokenizer}
    raise FileNotFoundError(f"No saved model found for '{model_name}' in {models_dir}")


def predict_headlines(headlines, best_model):
    cleaned = [clean_text(h) for h in headlines]
    if best_model["type"] == "ml":
        X = best_model["vectorizer"].transform(cleaned)
        proba = best_model["model"].predict_proba(X)[:, 1]
    else:
        from src.train_dl_models import to_padded_sequences
        X = to_padded_sequences(best_model["tokenizer"], cleaned)
        proba = best_model["model"].predict(X, verbose=0).ravel()

    results = []
    for headline, p in zip(headlines, proba):
        label = "REAL" if p >= 0.5 else "FAKE"
        confidence = p if p >= 0.5 else 1 - p
        results.append({"headline": headline, "prediction": label, "confidence": round(float(confidence), 3)})
    return results


def check_live_news(model_name, models_dir, feed_url=None, limit=15):
    best_model = load_best_model(model_name, models_dir)
    headlines = fetch_live_headlines(feed_url, limit)
    results = predict_headlines(headlines, best_model)
    for r in results:
        print(f"[{r['prediction']:4s} | conf={r['confidence']:.2f}] {r['headline']}")
    return results
