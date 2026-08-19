from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

RULE_FIELDS = {
    "High transaction value": ("total_BTC", 0.99),
    "High input count": ("num_input_addresses", 0.95),
    "High output count": ("num_output_addresses", 0.95),
    "High input degree": ("in_txs_degree", 0.95),
    "High output degree": ("out_txs_degree", 0.95),
    "High transaction size": ("size", 0.95),
}

@dataclass
class Indicator:
    name: str
    triggered: bool
    explanation: str

class ForensicRuleEngine:
    def __init__(self, training_frame: pd.DataFrame):
        self.thresholds = {}
        for name, (field, percentile) in RULE_FIELDS.items():
            values = pd.to_numeric(training_frame.get(field), errors="coerce").dropna()
            self.thresholds[field] = float(values.quantile(percentile)) if not values.empty else None
        self.percentiles = {field: percentile for field, percentile in (value for value in RULE_FIELDS.values())}

    def analyze(self, transaction: pd.Series, graph_stats: dict[str, Any] | None = None) -> list[Indicator]:
        indicators = []
        for name, (field, percentile) in RULE_FIELDS.items():
            value = pd.to_numeric(pd.Series([transaction.get(field)]), errors="coerce").iloc[0]
            threshold = self.thresholds.get(field)
            triggered = pd.notna(value) and threshold is not None and value >= threshold
            if triggered:
                explanation = f"{field} is {float(value):,.4g}, at or above the training-data {percentile:.0%} percentile ({threshold:,.4g})."
            elif pd.isna(value):
                explanation = f"{field} is unavailable for this transaction."
            else:
                explanation = f"{field} is below the training-data {percentile:.0%} percentile threshold."
            indicators.append(Indicator(name, bool(triggered), explanation))
        stats = graph_stats or {}
        for name, key, label in [("High fan-in", "in_degree", "incoming network degree"), ("High fan-out", "out_degree", "outgoing network degree")]:
            value = stats.get(key, 0); triggered = value >= 5
            indicators.append(Indicator(name, triggered, f"Selected node has {value} {label}; local structural review is recommended." if triggered else f"Selected node has {value} {label}; no high-{key.replace('_', '-')} pattern detected."))
        return indicators

    @staticmethod
    def risk_level(indicators: list[Indicator], prediction: int | None = None, probability: float | None = None) -> str:
        score = sum(item.triggered for item in indicators)
        if prediction == 1 and (probability or 0) >= 0.75: score += 2
        elif prediction == 1: score += 1
        return "HIGH" if score >= 5 else "MEDIUM" if score >= 3 else "LOW"
