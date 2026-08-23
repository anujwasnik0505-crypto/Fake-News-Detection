"""Train 5 classical ML models (TF-IDF features)."""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.calibration import CalibratedClassifierCV
from src.utils import MODELS_DIR, RANDOM_STATE

ML_MODELS = {
    "logistic_regression": LogisticRegression(max_iter=1000),
    "naive_bayes": MultinomialNB(),
    # LinearSVC has no predict_proba; calibrate it so we can plot ROC curves later
    "linear_svm": CalibratedClassifierCV(LinearSVC(random_state=RANDOM_STATE), cv=3),
    "random_forest": RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE),
    "decision_tree": DecisionTreeClassifier(random_state=RANDOM_STATE),
}


def train_ml_models(X_train, y_train):
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    X_train_tfidf = vectorizer.fit_transform(X_train)

    trained = {}
    for name, model in ML_MODELS.items():
        print(f"Training {name} ...")
        model.fit(X_train_tfidf, y_train)
        trained[name] = model
        joblib.dump(model, os.path.join(MODELS_DIR, f"{name}.joblib"))

    joblib.dump(vectorizer, os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
    return trained, vectorizer
