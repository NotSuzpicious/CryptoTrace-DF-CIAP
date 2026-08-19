from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

LABEL_MEANINGS = {1: "illicit", 2: "licit", 3: "unknown"}
CORE_FEATURES = [
    "Time step", "in_txs_degree", "out_txs_degree", "total_BTC", "fees", "size",
    "num_input_addresses", "num_output_addresses", "in_BTC_min", "in_BTC_max",
    "in_BTC_mean", "in_BTC_median", "in_BTC_total", "out_BTC_min", "out_BTC_max",
    "out_BTC_mean", "out_BTC_median", "out_BTC_total",
]

@dataclass
class DatasetSummary:
    feature_rows: int
    feature_columns: int
    class_rows: int
    edge_rows: int
    labelled_rows: int
    unknown_rows: int
    class_distribution: dict[str, int]
    missing_values: dict[str, int]
    duplicate_rows: dict[str, int]
    feature_ids_without_class: int
    class_ids_without_feature: int
    edge_endpoints_missing: int
    time_min: int | None
    time_max: int | None


def _read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required dataset file not found: {path}")
    try:
        frame = pd.read_csv(path, low_memory=False, **kwargs)
    except Exception as exc:
        raise ValueError(f"Could not read {path.name}: {exc}") from exc
    if frame.empty:
        raise ValueError(f"{path.name} is empty")
    return frame


def load_raw_dataset(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = Path(data_dir)
    features = _read_csv(root / "txs_features.csv")
    classes = _read_csv(root / "txs_classes.csv")
    edges = _read_csv(root / "txs_edgelist.csv")
    for frame, required, name in [
        (features, {"txId", "Time step"}, "txs_features.csv"),
        (classes, {"txId", "class"}, "txs_classes.csv"),
        (edges, {"txId1", "txId2"}, "txs_edgelist.csv"),
    ]:
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")
    return features, classes, edges


def summarize_dataset(data_dir: str | Path) -> DatasetSummary:
    features, classes, edges = load_raw_dataset(data_dir)
    feature_ids, class_ids = set(features.txId), set(classes.txId)
    endpoint_ids = set(edges.txId1) | set(edges.txId2)
    counts = classes["class"].value_counts(dropna=False).sort_index()
    return DatasetSummary(
        feature_rows=len(features), feature_columns=len(features.columns), class_rows=len(classes),
        edge_rows=len(edges), labelled_rows=int(classes["class"].isin([1, 2]).sum()),
        unknown_rows=int((classes["class"] == 3).sum()),
        class_distribution={str(k): int(v) for k, v in counts.items()},
        missing_values={str(k): int(v) for k, v in features.isna().sum().items() if v},
        duplicate_rows={"features": int(features.duplicated().sum()), "classes": int(classes.duplicated().sum()), "edges": int(edges.duplicated().sum())},
        feature_ids_without_class=len(feature_ids - class_ids), class_ids_without_feature=len(class_ids - feature_ids),
        edge_endpoints_missing=len(endpoint_ids - feature_ids),
        time_min=int(features["Time step"].min()), time_max=int(features["Time step"].max()),
    )


def _select_demo(test_features: pd.DataFrame, test_classes: pd.DataFrame) -> pd.DataFrame:
    labelled = test_features.merge(test_classes, on="txId", how="inner")
    pieces = []
    for label in (1, 2):
        group = labelled[labelled["class"] == label].sort_values("txId").head(20)
        pieces.append(group)
    return pd.concat(pieces, ignore_index=True).sort_values("txId")


def prepare_dataset(data_dir: str | Path, output_dir: str | Path, demo_dir: str | Path, seed: int = 42) -> dict[str, Any]:
    features, classes, edges = load_raw_dataset(data_dir)
    labelled = classes[classes["class"].isin([1, 2])].copy()
    train_ids, test_ids = train_test_split(
        labelled["txId"], test_size=0.20, random_state=seed, stratify=labelled["class"]
    )
    train_ids, test_ids = set(train_ids), set(test_ids)
    train_features = features[features.txId.isin(train_ids)].sort_values("txId")
    test_features = features[features.txId.isin(test_ids)].sort_values("txId")
    train_classes = classes[classes.txId.isin(train_ids)].sort_values("txId")
    test_classes = classes[classes.txId.isin(test_ids)].sort_values("txId")
    demo = _select_demo(test_features, test_classes)

    output = Path(output_dir); demo_root = Path(demo_dir)
    output.mkdir(parents=True, exist_ok=True); demo_root.mkdir(parents=True, exist_ok=True)
    train_features.to_csv(output / "train_features.csv", index=False)
    train_classes.to_csv(output / "train_classes.csv", index=False)
    test_features.to_csv(output / "test_features.csv", index=False)
    test_classes.to_csv(output / "test_classes.csv", index=False)
    demo.to_csv(demo_root / "demo_transactions.csv", index=False)
    edges.to_csv(output / "edges.csv", index=False)
    metadata = {"seed": seed, "label_meanings": LABEL_MEANINGS, "core_features": CORE_FEATURES,
                "train_rows": len(train_features), "test_rows": len(test_features), "demo_rows": len(demo),
                "train_ids": len(train_ids), "test_ids": len(test_ids)}
    (output / "split_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def feature_columns(frame: pd.DataFrame, mode: str = "core") -> list[str]:
    if mode == "core":
        missing = [column for column in CORE_FEATURES if column not in frame.columns]
        if missing:
            raise ValueError(f"Uploaded data is missing model features: {', '.join(missing)}")
        return CORE_FEATURES.copy()
    return [column for column in frame.columns if column != "txId" and pd.api.types.is_numeric_dtype(frame[column])]
