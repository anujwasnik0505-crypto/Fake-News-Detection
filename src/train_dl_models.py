"""Train 2 deep learning models: BiLSTM and Text-CNN (Keras)."""
import os
import pickle
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Embedding, Bidirectional, LSTM, Dense, Dropout,
    Conv1D, GlobalMaxPooling1D
)
from tensorflow.keras.callbacks import EarlyStopping
from src.utils import MODELS_DIR, MAX_VOCAB, MAX_LEN

EMBED_DIM = 100


def build_tokenizer(X_train):
    tokenizer = Tokenizer(num_words=MAX_VOCAB, oov_token="<OOV>")
    tokenizer.fit_on_texts(X_train)
    with open(os.path.join(MODELS_DIR, "tokenizer.pkl"), "wb") as f:
        pickle.dump(tokenizer, f)
    return tokenizer


def to_padded_sequences(tokenizer, texts):
    seqs = tokenizer.texts_to_sequences(texts)
    return pad_sequences(seqs, maxlen=MAX_LEN, padding="post", truncating="post")


def build_bilstm():
    model = Sequential([
        Embedding(MAX_VOCAB, EMBED_DIM, input_length=MAX_LEN),
        Bidirectional(LSTM(64, return_sequences=False)),
        Dropout(0.4),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def build_textcnn():
    model = Sequential([
        Embedding(MAX_VOCAB, EMBED_DIM, input_length=MAX_LEN),
        Conv1D(128, 5, activation="relu"),
        GlobalMaxPooling1D(),
        Dense(64, activation="relu"),
        Dropout(0.4),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train_dl_models(X_train, y_train, X_val, y_val, epochs=6, batch_size=64):
    tokenizer = build_tokenizer(X_train)
    X_train_pad = to_padded_sequences(tokenizer, X_train)
    X_val_pad = to_padded_sequences(tokenizer, X_val)

    es = EarlyStopping(monitor="val_loss", patience=2, restore_best_weights=True)
    trained = {}

    for name, builder in [("bilstm", build_bilstm), ("textcnn", build_textcnn)]:
        print(f"Training {name} ...")
        model = builder()
        model.fit(
            X_train_pad, y_train,
            validation_data=(X_val_pad, y_val),
            epochs=epochs, batch_size=batch_size,
            callbacks=[es], verbose=2,
        )
        model.save(os.path.join(MODELS_DIR, f"{name}.keras"))
        trained[name] = model

    return trained, tokenizer
