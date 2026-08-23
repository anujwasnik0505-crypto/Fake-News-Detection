"""Evaluate all 7 models: metrics table, ROC curves, confusion matrices."""
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix
)
from src.utils import OUTPUT_DIR
from src.train_dl_models import to_padded_sequences

sns.set_theme(style="whitegrid")


def _metrics(y_true, y_pred, y_proba):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_proba),
    }


def evaluate_all(ml_models, vectorizer, dl_models, tokenizer, X_test, y_test):
    results = {}
    roc_data = {}

    X_test_tfidf = vectorizer.transform(X_test)
    for name, model in ml_models.items():
        y_proba = model.predict_proba(X_test_tfidf)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)
        results[name] = _metrics(y_test, y_pred, y_proba)
        roc_data[name] = roc_curve(y_test, y_proba)

    X_test_pad = to_padded_sequences(tokenizer, X_test)
    for name, model in dl_models.items():
        y_proba = model.predict(X_test_pad, verbose=0).ravel()
        y_pred = (y_proba >= 0.5).astype(int)
        results[name] = _metrics(y_test, y_pred, y_proba)
        roc_data[name] = roc_curve(y_test, y_proba)

    results_df = pd.DataFrame(results).T.sort_values("f1", ascending=False)
    results_df.to_csv(os.path.join(OUTPUT_DIR, "model_comparison.csv"))

    _plot_bar_chart(results_df)
    _plot_roc_curves(roc_data, results)
    _plot_confusion_matrices(ml_models, dl_models, vectorizer, tokenizer, X_test, y_test)

    best_model_name = results_df.index[0]
    with open(os.path.join(OUTPUT_DIR, "best_model.json"), "w") as f:
        json.dump({"best_model": best_model_name, "f1": results_df.loc[best_model_name, "f1"]}, f, indent=2)

    print("\n=== Model comparison (sorted by F1) ===")
    print(results_df.round(4))
    print(f"\nBest model: {best_model_name}")
    return results_df, best_model_name


def _plot_bar_chart(results_df):
    ax = results_df[["accuracy", "precision", "recall", "f1"]].plot(kind="bar", figsize=(11, 6))
    ax.set_title("Model Comparison: Fake News Detection")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "comparison_bar_chart.png"), dpi=150)
    plt.close()


def _plot_roc_curves(roc_data, results):
    plt.figure(figsize=(8, 7))
    for name, (fpr, tpr, _) in roc_data.items():
        plt.plot(fpr, tpr, label=f"{name} (AUC={results[name]['roc_auc']:.3f})")
    plt.plot([0, 1], [0, 1], "k--", linewidth=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves — All Models")
    plt.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "roc_curves.png"), dpi=150)
    plt.close()


def _plot_confusion_matrices(ml_models, dl_models, vectorizer, tokenizer, X_test, y_test):
    all_models = list(ml_models.items()) + list(dl_models.items())
    n = len(all_models)
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    axes = axes.ravel()

    X_test_tfidf = vectorizer.transform(X_test)
    X_test_pad = to_padded_sequences(tokenizer, X_test)

    for i, (name, model) in enumerate(all_models):
        if name in ml_models:
            y_pred = model.predict(X_test_tfidf)
        else:
            y_pred = (model.predict(X_test_pad, verbose=0).ravel() >= 0.5).astype(int)
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[i],
                    xticklabels=["Fake", "Real"], yticklabels=["Fake", "Real"])
        axes[i].set_title(name)

    for j in range(n, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "confusion_matrices.png"), dpi=150)
    plt.close()
