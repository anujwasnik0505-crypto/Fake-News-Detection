"""Shared constants and data loading."""
import os
# NOTE: pandas / sklearn / preprocess (nltk) are imported lazily inside the
# functions below, not at module level — training scripts need them, but the
# webapp only needs the path constants below, so this keeps its memory
# footprint small on hosts with limited RAM (e.g. free-tier deployments).

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42
MAX_VOCAB = 8000
MAX_LEN = 25  # headlines are short


def load_dataset():
    """Load Kaggle Fake and Real News dataset (Fake.csv + True.csv from data/)."""
    import pandas as pd
    from src.preprocess import clean_series

    fake_path = os.path.join(DATA_DIR, "Fake.csv")
    true_path = os.path.join(DATA_DIR, "True.csv")
    if not (os.path.exists(fake_path) and os.path.exists(true_path)):
        raise FileNotFoundError(
            "Place Fake.csv and True.csv (Kaggle 'Fake and Real News Dataset') inside the data/ folder."
        )
    fake = pd.read_csv(fake_path)
    true = pd.read_csv(true_path)
    fake["label"] = 0  # 0 = fake
    true["label"] = 1  # 1 = real
    df = pd.concat([fake[["title", "label"]], true[["title", "label"]]], ignore_index=True)
    df.dropna(subset=["title"], inplace=True)
    df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)  # shuffle
    df["clean_title"] = clean_series(df["title"])
    return df


def split_data(df):
    from sklearn.model_selection import train_test_split
    return train_test_split(
        df["clean_title"], df["label"], test_size=0.2,
        random_state=RANDOM_STATE, stratify=df["label"]
    )
