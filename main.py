"""
Fake News Detection — full pipeline
Train 5 ML models + 2 DL models, evaluate, then classify real-time news headlines.

Usage:
    python main.py            # train + evaluate + check live news
    python main.py --skip-train   # reuse saved models, only check live news
"""
import argparse
import json
import os

from src.utils import load_dataset, split_data, MODELS_DIR, OUTPUT_DIR
from src.train_ml_models import train_ml_models
from src.train_dl_models import train_dl_models
from src.evaluate import evaluate_all
from src.realtime_news import check_live_news


def main(skip_train=False, feed_url=None):
    if not skip_train:
        print("Loading and cleaning dataset ...")
        df = load_dataset()
        X_train, X_test, y_train, y_test = split_data(df)

        print("\n--- Training 5 classical ML models ---")
        ml_models, vectorizer = train_ml_models(X_train, y_train)

        print("\n--- Training 2 deep learning models ---")
        dl_models, tokenizer = train_dl_models(X_train, y_train, X_test, y_test)

        print("\n--- Evaluating all 7 models ---")
        results_df, best_model_name = evaluate_all(
            ml_models, vectorizer, dl_models, tokenizer, X_test, y_test
        )
    else:
        with open(os.path.join(OUTPUT_DIR, "best_model.json")) as f:
            best_model_name = json.load(f)["best_model"]
        print(f"Reusing saved best model: {best_model_name}")

    print(f"\n--- Checking real-time news headlines using best model: {best_model_name} ---")
    check_live_news(best_model_name, MODELS_DIR, feed_url=feed_url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true", help="Skip training, reuse saved models")
    parser.add_argument("--feed-url", default=None, help="Custom RSS feed URL for live news")
    args = parser.parse_args()
    main(skip_train=args.skip_train, feed_url=args.feed_url)
