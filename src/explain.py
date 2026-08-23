"""
Explainable AI layer.

Explains WHICH WORDS in a headline influenced the model's
REAL / FAKE prediction.

Methods:
    - LIME
    - SHAP

The function works with the project's existing model format:

ML:
{
    "type": "ml",
    "vectorizer": ...,
    "model": ...
}

DL:
{
    "type": "dl",
    "tokenizer": ...,
    "model": ...
}
"""

import numpy as np

from src.preprocess import clean_text

# ============================================================
# PROBABILITY FUNCTION
# ============================================================

def _proba_fn_factory(best_model):
    """
    Returns:

        list[str]
            ->
        numpy array of shape (n, 2)

    Column 0 = P(FAKE)
    Column 1 = P(REAL)
    """

    def proba_fn(texts):
        texts = list(texts)

        cleaned = [
            clean_text(text)
            for text in texts
        ]

        # ----------------------------------------------------
        # ML MODEL
        # ----------------------------------------------------

        if best_model["type"] == "ml":
            vectorizer = best_model["vectorizer"]
            model = best_model["model"]

            X = vectorizer.transform(cleaned)

            p_real = model.predict_proba(X)[:, 1]

        # ----------------------------------------------------
        # DEEP LEARNING MODEL
        # ----------------------------------------------------

        else:
            from src.train_dl_models import (
                to_padded_sequences
            )

            tokenizer = best_model["tokenizer"]
            model = best_model["model"]

            X = to_padded_sequences(
                tokenizer,
                cleaned
            )

            prediction = model.predict(
                X,
                verbose=0
            )

            p_real = np.asarray(
                prediction
            ).ravel()

        # ----------------------------------------------------
        # SAFE RANGE
        # ----------------------------------------------------

        p_real = np.clip(
            np.asarray(
                p_real,
                dtype=float
            ),
            0.0,
            1.0
        )

        return np.column_stack([
            1.0 - p_real,
            p_real
        ])

    return proba_fn

# ============================================================
# LIME
# ============================================================

def explain_with_lime(
    headline,
    best_model,
    num_features=12
):
    """
    LIME explanation.

    Positive weight:
        pushes prediction toward REAL.

    Negative weight:
        pushes prediction toward FAKE.
    """

    from lime.lime_text import (
        LimeTextExplainer
    )

    proba_fn = _proba_fn_factory(
        best_model
    )

    explainer = LimeTextExplainer(
        class_names=[
            "FAKE",
            "REAL"
        ]
    )

    explanation = explainer.explain_instance(
        headline,
        proba_fn,
        num_features=num_features,
        labels=[1]
    )

    pairs = explanation.as_list(
        label=1
    )

    words = []

    for word, weight in pairs:
        weight = float(weight)

        words.append({
            "word": str(word),
            "weight": round(weight, 4),
            "impact": (
                "REAL"
                if weight >= 0
                else "FAKE"
            )
        })

    words.sort(
        key=lambda item: -abs(
            item["weight"]
        )
    )

    return {
        "method": "lime",
        "words": words
    }

# ============================================================
# SHAP
# ============================================================

def explain_with_shap(
    headline,
    best_model,
    num_features=12
):
    """
    SHAP text explanation.

    Positive:
        supports REAL.

    Negative:
        supports FAKE.
    """

    import shap

    proba_fn = _proba_fn_factory(
        best_model
    )

    masker = shap.maskers.Text()

    explainer = shap.Explainer(
        proba_fn,
        masker,
        output_names=[
            "FAKE",
            "REAL"
        ]
    )

    shap_values = explainer(
        [headline]
    )

    values = np.asarray(
        shap_values[0].values
    )

    tokens = shap_values[0].data

    # --------------------------------------------------------
    # SHAP output can have different dimensions depending
    # on SHAP version/model wrapper.
    # --------------------------------------------------------

    if values.ndim == 2:
        if values.shape[1] >= 2:
            real_values = values[:, 1]
        else:
            real_values = values[:, 0]
    else:
        real_values = values.ravel()

    pairs = []

    for token, value in zip(
        tokens,
        real_values
    ):
        token = str(token).strip()

        if not token:
            continue

        value = float(value)

        pairs.append(
            (
                token,
                value
            )
        )

    pairs.sort(
        key=lambda item: -abs(
            item[1]
        )
    )

    pairs = pairs[:num_features]

    words = []

    for word, weight in pairs:
        words.append({
            "word": word,
            "weight": round(
                float(weight),
                4
            ),
            "impact": (
                "REAL"
                if weight >= 0
                else "FAKE"
            )
        })

    return {
        "method": "shap",
        "words": words
    }

# ============================================================
# MAIN FUNCTION
# ============================================================

def explain_headline(
    headline,
    best_model,
    method="lime",
    num_features=12
):
    """
    Main public function.

    method:
        "lime"
        "shap"
    """

    headline = str(
        headline
    ).strip()

    if not headline:
        raise ValueError(
            "Headline cannot be empty."
        )

    method = str(
        method
    ).lower().strip()

    if method == "shap":
        result = explain_with_shap(
            headline,
            best_model,
            num_features
        )
    else:
        result = explain_with_lime(
            headline,
            best_model,
            num_features
        )

    # --------------------------------------------------------
    # Add model prediction
    # --------------------------------------------------------

    probabilities = _proba_fn_factory(
        best_model
    )([headline])

    p_fake = float(
        probabilities[0][0]
    )

    p_real = float(
        probabilities[0][1]
    )

    prediction = (
        "REAL"
        if p_real >= p_fake
        else "FAKE"
    )

    result["headline"] = headline
    result["prediction"] = prediction

    result["probability"] = {
        "fake": round(
            p_fake,
            4
        ),
        "real": round(
            p_real,
            4
        )
    }

    return result