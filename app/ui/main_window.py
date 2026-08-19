from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import networkx as nx
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QPlainTextEdit, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from app.analysis.forensic_rules import ForensicRuleEngine
from app.analysis.preprocessing import LABEL_MEANINGS, load_raw_dataset, summarize_dataset
from app.graph.graph_analysis import obfuscation_indicators
from app.graph.graph_builder import TransactionGraph
from app.ml.model_manager import ModelManager
from app.reports.forensic_report import generate_report

ROOT = Path(__file__).resolve().parents[2]

class NetworkCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self._graph = nx.DiGraph()
        self._selected = None

    def set_graph(self, graph, selected):
        self._graph = graph.copy()
        self._selected = selected
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d141b"))
        if not self._graph:
            painter.setPen(QColor("#9fb2c1"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Choose a transaction and explore its network")
            return
        nodes = list(self._graph.nodes())
        positions = nx.spring_layout(self._graph, seed=42)
        minimum_x = min(point[0] for point in positions.values())
        maximum_x = max(point[0] for point in positions.values())
        minimum_y = min(point[1] for point in positions.values())
        maximum_y = max(point[1] for point in positions.values())
        width = max(maximum_x - minimum_x, 0.01)
        height = max(maximum_y - minimum_y, 0.01)
        margin = 45
        points = {node: QPointF(margin + (point[0] - minimum_x) / width * (self.width() - 2 * margin), margin + (maximum_y - point[1]) / height * (self.height() - 2 * margin)) for node, point in positions.items()}
        painter.setPen(QPen(QColor("#607785"), 1))
        for source, target in self._graph.edges():
            start, end = points[source], points[target]
            painter.drawLine(start, end)
            direction = end - start
            length = max((direction.x() ** 2 + direction.y() ** 2) ** 0.5, 1)
            unit_x, unit_y = direction.x() / length, direction.y() / length
            tip = end - QPointF(unit_x * 10, unit_y * 10)
            left = tip - QPointF(unit_x * 8 - unit_y * 4, unit_y * 8 + unit_x * 4)
            right = tip - QPointF(unit_x * 8 + unit_y * 4, unit_y * 8 - unit_x * 4)
            painter.setBrush(QColor("#607785")); painter.drawPolygon(QPolygonF([tip, left, right]))
        for node in nodes:
            point = points[node]
            selected = node == self._selected
            painter.setPen(QPen(QColor("#f0c674") if selected else QColor("#0b1117"), 2))
            painter.setBrush(QColor("#f0c674") if selected else QColor("#55c7b5"))
            painter.drawEllipse(point, 9 if selected else 7, 9 if selected else 7)
            painter.setPen(QColor("#dbe7ef"))
            painter.drawText(point + QPointF(12, 4), str(node))

class CryptoTraceWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("CryptoTrace | Cryptocurrency Transaction Forensics"); self.resize(1280, 800)
        self.features = pd.DataFrame(); self.classes = pd.DataFrame(); self.edges = pd.DataFrame(); self.current = None
        self.model = ModelManager(ROOT / "models")
        try:
            self.features, self.classes, self.edges = load_raw_dataset(ROOT)
            train_path = ROOT / "data" / "processed" / "train_features.csv"
            self.rules = ForensicRuleEngine(pd.read_csv(train_path) if train_path.exists() else self.features)
            self.graph = TransactionGraph(ROOT / "data" / "processed" / "edges.csv") if (ROOT / "data" / "processed" / "edges.csv").exists() else None
        except Exception as exc:
            self.rules = None; self.graph = None; self.startup_error = str(exc)
        self._build_ui(); self._refresh_dashboard()

    def _build_ui(self):
        root = QWidget(); layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0)
        self.nav = QListWidget(); self.nav.setFixedWidth(235); self.nav.addItems(["Dashboard", "Transaction Investigation", "Network Analysis", "Suspicious Activity", "Model Validation", "Case Management", "Reports"])
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex if hasattr(self, "pages") else lambda _: None)
        layout.addWidget(self.nav); self.pages = QStackedWidget(); layout.addWidget(self.pages, 1); self.setCentralWidget(root)
        self.dashboard = self._dashboard_page(); self.investigation = self._investigation_page(); self.network = self._network_page(); self.flow = self._flow_page(); self.suspicious = self._suspicious_page(); self.validation = self._validation_page(); self.case = self._case_page(); self.reports = self._reports_page()
        for page in [self.dashboard, self.investigation, self.network, self.flow, self.suspicious, self.validation, self.case, self.reports]: self.pages.addWidget(page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex); self.nav.setCurrentRow(0)

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); heading = QLabel(title); heading.setObjectName("PageTitle"); layout.addWidget(heading); layout.addWidget(QLabel(subtitle)); return page, layout

    def _dashboard_page(self):
        page, layout = self._page("Forensic Dashboard", "Local analytical overview. Model predictions and rules are investigative indicators, not legal conclusions.")
        self.dashboard_grid = QGridLayout(); layout.addLayout(self.dashboard_grid); actions = QHBoxLayout(); demo = QPushButton("Run Demo Investigation"); demo.clicked.connect(self._load_demo); load = QPushButton("Load CSV"); load.clicked.connect(self._load_csv); actions.addWidget(demo); actions.addWidget(load); actions.addStretch(); layout.addLayout(actions); return page

    def _metric(self, label, value):
        box = QGroupBox(label); box.setMinimumHeight(80); v = QVBoxLayout(box); text = QLabel(str(value)); text.setObjectName("Metric"); v.addWidget(text); return box

    def _refresh_dashboard(self):
        if not hasattr(self, "dashboard_grid"): return
        while self.dashboard_grid.count(): self.dashboard_grid.takeAt(0).widget().deleteLater()
        if self.features.empty:
            self.dashboard_grid.addWidget(self._metric("Dataset", "Not loaded"), 0, 0); return
        summary = summarize_dataset(ROOT); values = [("Transactions", summary.feature_rows), ("Labelled", summary.labelled_rows), ("Unknown", summary.unknown_rows), ("Edges", summary.edge_rows), ("Time range", f"{summary.time_min} - {summary.time_max}"), ("Model status", "Loaded" if self.model.available else "Not trained")]
        for index, (label, value) in enumerate(values): self.dashboard_grid.addWidget(self._metric(label, value), index // 3, index % 3)
        self.dashboard_grid.addWidget(self._metric("Class distribution", "1 illicit / 2 licit / 3 unknown"), 2, 0, 1, 3)

    def _investigation_page(self):
        page, layout = self._page("Transaction Investigation", "Inspect features, model assessment, rule explanations, and risk level for one transaction.")
        row = QHBoxLayout(); self.tx_input = QLineEdit(); self.tx_input.setPlaceholderText("Enter txId"); go = QPushButton("Investigate"); go.clicked.connect(self._investigate); row.addWidget(self.tx_input); row.addWidget(go); layout.addLayout(row); self.investigation_text = QPlainTextEdit(); self.investigation_text.setReadOnly(True); layout.addWidget(self.investigation_text); return page

    def _network_page(self):
        page, layout = self._page("Network Analysis", "Bounded 1-3 hop directed transaction graph around the selected node."); row = QHBoxLayout(); self.hop = QSpinBox(); self.hop.setRange(1, 3); self.hop.setValue(1); button = QPushButton("Explore selected transaction"); button.clicked.connect(self._show_network); row.addWidget(QLabel("Hops")); row.addWidget(self.hop); row.addWidget(button); row.addStretch(); layout.addLayout(row); self.network_canvas = NetworkCanvas(); layout.addWidget(self.network_canvas); self.network_text = QPlainTextEdit(); self.network_text.setReadOnly(True); layout.addWidget(self.network_text); return page

    def _flow_page(self):
        page, layout = self._page("Fund Flow", "Trace local graph paths forward or backward without assigning real-world ownership."); row = QHBoxLayout(); self.flow_direction = QLineEdit("forward"); self.flow_depth = QSpinBox(); self.flow_depth.setRange(1, 3); self.flow_depth.setValue(3); button = QPushButton("Trace flow"); button.clicked.connect(self._show_flow); row.addWidget(QLabel("Direction (forward/backward)")); row.addWidget(self.flow_direction); row.addWidget(QLabel("Depth")); row.addWidget(self.flow_depth); row.addWidget(button); row.addStretch(); layout.addLayout(row); self.flow_text = QPlainTextEdit(); self.flow_text.setReadOnly(True); layout.addWidget(self.flow_text); return page

    def _suspicious_page(self):
        page, layout = self._page("Suspicious Activity", "Filter model predictions and explainable indicators for further investigation."); button = QPushButton("Show flagged demo transactions"); button.clicked.connect(self._show_suspicious); layout.addWidget(button); self.suspicious_text = QPlainTextEdit(); self.suspicious_text.setReadOnly(True); layout.addWidget(self.suspicious_text); return page

    def _validation_page(self):
        page, layout = self._page("Model Validation", "Metrics shown here are calculated on the held-out test dataset. The demo set is excluded."); self.validation_text = QPlainTextEdit(); self.validation_text.setReadOnly(True); layout.addWidget(self.validation_text); return page

    def _case_page(self):
        page, layout = self._page("Case Management", "Case context is stored for the current local investigation and embedded in reports."); form = QFormLayout(); self.case_id = QLineEdit("CT-2026-001"); self.case_name = QLineEdit("Suspicious Transaction Investigation"); self.investigator = QLineEdit(); self.case_notes = QPlainTextEdit(); form.addRow("Case ID", self.case_id); form.addRow("Case name", self.case_name); form.addRow("Investigator", self.investigator); form.addRow("Notes", self.case_notes); layout.addLayout(form); save = QPushButton("Save case JSON"); save.clicked.connect(self._save_case); layout.addWidget(save); return page

    def _reports_page(self):
        page, layout = self._page("Reports", "Generate a local PDF containing the selected transaction analysis and explicit limitations."); button = QPushButton("Generate PDF forensic report"); button.clicked.connect(self._generate_report); layout.addWidget(button); self.report_text = QLabel("No report generated."); layout.addWidget(self.report_text); layout.addStretch(); return page

    def _load_demo(self):
        path = ROOT / "data" / "demo" / "demo_transactions.csv"
        if not path.exists(): return self._error("Demo data is not prepared. Run scripts/prepare_dataset.py first.")
        demo = pd.read_csv(path); selected = demo[demo["class"] == 1].iloc[0]; self.tx_input.setText(str(int(selected.txId))); self._investigate(); self.nav.setCurrentRow(1)

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load transaction CSV", str(ROOT), "CSV files (*.csv)")
        if not path: return
        try:
            frame = pd.read_csv(path, low_memory=False)
            if "txId" not in frame: raise ValueError("CSV must contain a txId column.")
            if self.model.available: predictions = self.model.predict_frame(frame); frame = frame.merge(predictions, on="txId", how="left")
            self.features = frame; self._refresh_dashboard(); QMessageBox.information(self, "CSV loaded", f"Loaded {len(frame):,} transactions. The saved model was used; no retraining occurred.")
        except Exception as exc: self._error(str(exc))

    def _selected_id(self):
        try: return int(self.tx_input.text().strip())
        except ValueError: raise ValueError("Enter a numeric transaction ID.")

    def _transaction(self, tx_id):
        rows = self.features[self.features.txId == tx_id]
        if rows.empty: raise ValueError(f"Transaction {tx_id} was not found in the loaded dataset.")
        return rows.iloc[0]

    def _investigate(self):
        try:
            tx_id = self._selected_id(); tx = self._transaction(tx_id); graph_stats = self.graph.stats(tx_id) if self.graph else {}; indicators = self.rules.analyze(tx, graph_stats) if self.rules else []
            prediction_text = "Model unavailable"; prediction = None; probability = None
            if self.model.available:
                prediction_row = self.model.predict_frame(pd.DataFrame([tx])) .iloc[0]; prediction = int(prediction_row.prediction); probability = float(prediction_row.model_probability); prediction_text = f"{prediction_row.prediction_name} ({probability:.1%})"
            ground = self.classes.loc[self.classes.txId == tx_id, "class"]
            risk = self.rules.risk_level(indicators, prediction, probability) if self.rules else "Unavailable"; self.current = {"tx_id": tx_id, "tx": tx, "indicators": indicators, "prediction": prediction, "probability": probability, "risk": risk}
            lines = [f"Transaction: {tx_id}", f"Ground truth: {LABEL_MEANINGS.get(int(ground.iloc[0]), 'unavailable') if not ground.empty else 'unavailable'}", f"Model assessment: {prediction_text}", f"Overall investigation risk: {risk}", "", "Transaction features:"]
            for key in ["Time step", "total_BTC", "fees", "size", "in_txs_degree", "out_txs_degree", "num_input_addresses", "num_output_addresses"]:
                if key in tx: lines.append(f"  {key}: {tx[key]}")
            lines += ["", "Forensic indicators:"] + [f"  {'[x]' if item.triggered else '[ ]'} {item.name}: {item.explanation}" for item in indicators]
            obfuscation = obfuscation_indicators(self.graph, tx_id) if self.graph else []; lines += ["", "Potential obfuscation indicators:"] + ([f"  {item}" for item in obfuscation] or ["  None detected in the selected local neighborhood."]); self.investigation_text.setPlainText("\n".join(lines))
        except Exception as exc: self._error(str(exc))

    def _show_network(self):
        if not self.current or not self.graph: return self._error("Investigate a transaction after preparing the graph.")
        subgraph = self.graph.neighborhood(self.current["tx_id"], self.hop.value()); lines = [f"Selected node: {self.current['tx_id']}", f"Nodes: {subgraph.number_of_nodes()} | Edges: {subgraph.number_of_edges()}", "", "Relationships:"]
        lines += [f"  {source} -> {target}" for source, target in list(subgraph.edges())[:150]]; self.network_text.setPlainText("\n".join(lines))
        self.network_canvas.set_graph(subgraph, self.current["tx_id"])

    def _show_flow(self):
        if not self.current or not self.graph: return self._error("Investigate a transaction first.")
        direction = self.flow_direction.text().strip().lower()
        if direction not in {"forward", "backward"}: return self._error("Direction must be forward or backward.")
        paths = self.graph.flow(self.current["tx_id"], direction, self.flow_depth.value()); self.flow_text.setPlainText("\n".join(" -> ".join(map(str, path)) for path in paths) or "No local paths found.")

    def _show_suspicious(self):
        if not self.model.available: return self._error("Model not found. Run scripts/train_model.py first.")
        sample = self.features.head(2000); results = self.model.predict_frame(sample); flagged = results[results.prediction == 1].head(20); self.suspicious_text.setPlainText("\n".join(f"{row.txId}: {row.model_probability:.1%} model probability for potentially illicit class" for row in flagged.itertuples()) or "No flagged rows in the sample.")

    def _refresh_validation(self):
        if not self.model.metadata: self.validation_text.setPlainText("Model status: not trained\nRun python scripts/train_model.py after preparation."); return
        metrics = self.model.metadata.get("metrics", {}); text = ["MODEL STATUS: trained model loaded", f"Train rows: {self.model.metadata.get('train_rows'):,}", f"Held-out test rows: {self.model.metadata.get('test_rows'):,}", "", "Class-1 (illicit) metrics", f"Precision: {metrics.get('precision', 0):.3f}", f"Recall: {metrics.get('recall', 0):.3f}", f"F1: {metrics.get('f1', 0):.3f}", f"Accuracy: {metrics.get('accuracy', 0):.3f}", f"ROC-AUC: {metrics.get('roc_auc', 0):.3f}", f"PR-AUC: {metrics.get('pr_auc', 0):.3f}", f"Confusion matrix [class 1, class 2]: {metrics.get('confusion_matrix')}"]; self.validation_text.setPlainText("\n".join(text))

    def _save_case(self):
        case = {"case_id": self.case_id.text(), "case_name": self.case_name.text(), "investigator": self.investigator.text(), "notes": self.case_notes.toPlainText()}; (ROOT / "reports").mkdir(exist_ok=True); (ROOT / "reports" / "current_case.json").write_text(json.dumps(case, indent=2), encoding="utf-8"); QMessageBox.information(self, "Case saved", "Case information saved locally.")

    def _generate_report(self):
        if not self.current: return self._error("Investigate a transaction first.")
        case = {"case_id": self.case_id.text(), "case_name": self.case_name.text(), "investigator": self.investigator.text(), "notes": self.case_notes.toPlainText()}; destination, _ = QFileDialog.getSaveFileName(self, "Save forensic report", str(ROOT / "reports" / f"CryptoTrace_{self.current['tx_id']}.pdf"), "PDF files (*.pdf)")
        if not destination: return
        try:
            tx = self.current["tx"]; details = {key: tx.get(key) for key in ["txId", "Time step", "total_BTC", "fees", "size", "in_txs_degree", "out_txs_degree"]}; indicators = [{"name": i.name, "explanation": i.explanation} for i in self.current["indicators"]]; generate_report(destination, case, {"details": details, "model": f"Prediction: {self.current['prediction']}; probability: {self.current['probability']}", "indicators": indicators, "risk": self.current["risk"]}); self.report_text.setText(f"Report generated: {destination}")
        except Exception as exc: self._error(f"Report generation failed: {exc}")

    def _error(self, message): QMessageBox.warning(self, "CryptoTrace", message)

    def showEvent(self, event):
        super().showEvent(event); self._refresh_validation()

def run():
    app = QApplication.instance() or QApplication([]); app.setStyleSheet("""
        QWidget { background: #111820; color: #dbe7ef; font-size: 13px; }
        QListWidget { background: #0b1117; border: none; padding: 12px; }
        QListWidget::item { padding: 14px 10px; color: #9fb2c1; }
        QListWidget::item:selected { background: #1e3a4b; color: #7fe0d1; border-left: 3px solid #55c7b5; }
        QLineEdit, QPlainTextEdit, QSpinBox { background: #0d141b; border: 1px solid #2b3b47; border-radius: 3px; padding: 8px; }
        QPushButton { background: #1f6f73; border: none; padding: 10px 16px; border-radius: 3px; color: white; }
        QPushButton:hover { background: #2a8b88; }
        QGroupBox { border: 1px solid #2b3b47; margin-top: 12px; padding: 12px; }
        #PageTitle { font-size: 24px; font-weight: bold; color: #7fe0d1; }
        #Metric { font-size: 22px; font-weight: bold; color: #f0c674; }
    """); window = CryptoTraceWindow(); window.show(); app.exec()
