from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.analysis.preprocessing import feature_columns


class ModelManager:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.model = None
        self.pipeline = None
        self.metadata: dict[str, Any] = {}
        self.load()

    @property
    def available(self) -> bool:
        return self.model is not None and self.pipeline is not None

    def load(self) -> None:
        model_path = self.model_dir / "random_forest.joblib"
        pipeline_path = self.model_dir / "preprocessing.joblib"
        metadata_path = self.model_dir / "model_metadata.json"
        if model_path.exists() and pipeline_path.exists():
            self.model = joblib.load(model_path)
            self.pipeline = joblib.load(pipeline_path)
        if metadata_path.exists():
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    def predict_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.available:
            raise FileNotFoundError("Trained model not found. Run python scripts/train_model.py first.")
        columns = self.metadata.get("features") or feature_columns(frame, "core")
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError("Uploaded CSV is missing model columns: " + ", ".join(missing))
        transformed = self.pipeline.transform(frame[columns])
        predictions = self.model.predict(transformed)
        probabilities = self.model.predict_proba(transformed).max(axis=1)
        result = frame[["txId"]].copy() if "txId" in frame else pd.DataFrame(index=frame.index)
        result["prediction"] = predictions
        result["prediction_name"] = result["prediction"].map({1: "Potentially illicit", 2: "Potentially licit"}).fillna("Unknown")
        result["model_probability"] = probabilities
        return result
