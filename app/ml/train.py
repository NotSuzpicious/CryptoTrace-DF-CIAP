from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, average_precision_score, classification_report,
                             confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline

from app.analysis.preprocessing import feature_columns


def _metrics(model, pipeline, frame: pd.DataFrame, labels: pd.Series, features: list[str]) -> dict[str, Any]:
    transformed = pipeline.transform(frame[features])
    predicted = model.predict(transformed)
    probability = model.predict_proba(transformed)
    positive_index = list(model.classes_).index(1)
    return {
        "accuracy": float(accuracy_score(labels, predicted)),
        "precision": float(precision_score(labels, predicted, pos_label=1, zero_division=0)),
        "recall": float(recall_score(labels, predicted, pos_label=1, zero_division=0)),
        "f1": float(f1_score(labels, predicted, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels == 1, probability[:, positive_index])),
        "pr_auc": float(average_precision_score(labels == 1, probability[:, positive_index])),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=[1, 2]).tolist(),
        "classification_report": classification_report(labels, predicted, labels=[1, 2], target_names=["illicit", "licit"], output_dict=True, zero_division=0),
    }


def train_model(processed_dir: str | Path, model_dir: str | Path, seed: int = 42) -> dict[str, Any]:
    root, out = Path(processed_dir), Path(model_dir); out.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(root / "train_features.csv"); train_labels = pd.read_csv(root / "train_classes.csv")["class"]
    test = pd.read_csv(root / "test_features.csv"); test_labels = pd.read_csv(root / "test_classes.csv")["class"]
    features = feature_columns(train, "core")
    pipeline = Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True))])
    transformed_train = pipeline.fit_transform(train[features])
    model = RandomForestClassifier(n_estimators=180, class_weight="balanced", random_state=seed, n_jobs=-1, min_samples_leaf=2)
    model.fit(transformed_train, train_labels)
    metrics = _metrics(model, pipeline, test, test_labels, features)
    joblib.dump(model, out / "random_forest.joblib"); joblib.dump(pipeline, out / "preprocessing.joblib")
    metadata = {"model": "RandomForestClassifier", "features": features, "label_meanings": {"1": "illicit", "2": "licit", "3": "unknown"}, "positive_label": 1, "seed": seed, "train_rows": len(train), "test_rows": len(test), "metrics": metrics}
    (out / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
