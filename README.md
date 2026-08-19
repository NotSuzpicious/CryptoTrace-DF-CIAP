# CRYPTO TRACE

CryptoTrace is a standalone Python/PySide6 desktop application for academic cryptocurrency transaction forensic analysis. It is designed for the CCE project **Cryptocurrency Transaction Analysis for Digital Forensics** and runs locally against the supplied Elliptic transaction files. It is not a web application and has no blockchain API dependency.

## 1. Overview

The application combines dataset validation, transaction inspection, Random Forest classification, explainable forensic indicators, directed transaction-network analysis, local fund-flow tracing, potential obfuscation-pattern analysis, investigation risk assessment, held-out validation, case context, and PDF report generation.

The tool reports **potentially suspicious**, model-derived, or structural indicators. It does not prove criminal activity, identify a person, establish wallet ownership, or make legal attribution.

## 2. Dataset Findings

The supplied files were inspected before implementation:

- `txs_features.csv`: 203,769 rows, 184 columns, numeric feature matrix plus `txId` and `Time step`.
- `txs_classes.csv`: 203,769 rows, `txId` and `class`.
- `txs_edgelist.csv`: 234,355 directed edges, `txId1` to `txId2`.
- All feature and class transaction IDs match exactly.
- Every edge endpoint exists in the feature table.
- There are no duplicate rows.
- The 17 transaction-level BTC/address fields have 965 missing values each; these are median-imputed inside the training pipeline.
- Time steps span 1 to 49.
- Class distribution is class 1: 4,545, class 2: 42,019, class 3: 157,205.

The Elliptic dataset convention used here is class 1 = illicit, class 2 = licit, class 3 = unknown/unlabelled. This convention should be cross-checked against the dataset publication or supplied course documentation when presenting results.

## 3. Features and Methodology

The initial model uses 18 interpretable transaction-level fields: time step, transaction degrees, BTC totals/statistics, fees, size, and input/output address counts. This keeps the CIAP demonstration explainable. The feature-selection function also supports an inspected full numeric feature experiment without silently including `txId`.

The classifier is a `RandomForestClassifier` with `class_weight="balanced"`. The saved preprocessing pipeline contains a median imputer with missingness indicators. No preprocessing is fitted on the full dataset.

## 4. Leakage-Controlled Split

Only classes 1 and 2 are used for supervised learning. Class 3 remains unknown and is never used as a training label. The labelled data is stratified into an 80% training split and a 20% held-out test split using seed 42. The deterministic demonstration set contains 20 class-1 and 20 class-2 transactions selected from the held-out test data. It is never used in training.

Generated artifacts are stored under `data/processed/` and `data/demo/`; original CSVs are not modified.

## 5. Forensic Rules

Rules derive thresholds from the training-data distributions, primarily the 95th and 99th percentiles. Current indicators include high transaction value, input/output count, transaction size, input/output degree, fan-in, and fan-out. Each result includes the measured field and threshold rationale. Rules create investigation indicators only.

## 6. Graph and Fund Flow

The edge list is loaded into a directed NetworkX graph. The UI extracts only a bounded 1-, 2-, or 3-hop neighborhood for the selected transaction. Forward and backward flow tracing is depth-limited and caps branching for responsiveness. Graph nodes represent transaction IDs, not people or identities.

Structural analysis can label potential fan-in, fan-out, rapid splitting, and rapid recombination as **Potential Obfuscation Indicators**. It does not label a mixer or money laundering.

## 7. Risk Assessment

Model assessment, forensic indicators, network indicators, and potential obfuscation indicators are kept conceptually separate. A simple investigation risk level combines triggered rule count with a model prediction/probability for triage. The recommendation is further investigation, not a probability of crime.

## 8. Installation

Use Python 3.11+ on Windows, open PowerShell in the project directory, and install dependencies:

```powershell
python -m pip install -r requirements.txt
```

The tested environment used Python 3.14 and the packages listed in `requirements.txt`.

## 9. Prepare, Train, Evaluate

Run these explicit development/setup operations:

```powershell
python scripts/prepare_dataset.py
python scripts/train_model.py
python scripts/evaluate_model.py
```

The GUI never trains automatically. The model and imputer are saved in `models/` as joblib artifacts with `model_metadata.json`.

## 10. Run CryptoTrace

```powershell
python main.py
```

Use **Run Demo Investigation** for the deterministic CIAP walkthrough. It selects a known class-1 transaction from the fixed held-out demo set, then opens the investigation screen. Use the sidebar to inspect the dashboard, network, flow, suspicious activity, validation, case, and report views.

Use **Load CSV** for a compatible local feature CSV. It must contain `txId` and the saved model feature columns. The model is applied without retraining. Missing columns and invalid transaction IDs produce a message instead of a crash.

## 11. Reporting

Enter case ID, case name, investigator, and notes under Case Management. Investigate a transaction, open Reports, and generate a PDF. The report contains case context, transaction details, model assessment, rule explanations, risk level, notes, and the analytical disclaimer.

## 12. Validation Results

Validation metrics are calculated only on the held-out test dataset. The current core-feature model produces accuracy, class-1 precision/recall/F1, ROC-AUC, PR-AUC, and a 2x2 confusion matrix in `models/model_metadata.json`. Accuracy is shown for context and is not the primary decision metric because the labelled set is imbalanced.

## 13. Limitations and Future Work

This academic tool uses the supplied transaction graph and dataset labels only. It has no address attribution, live chain data, wallet clustering, temporal velocity model, calibrated probabilities, or legal evidentiary status. Future work can add cross-validation, a carefully documented full-feature experiment, richer temporal graph metrics, exportable graph images, and analyst-reviewed case storage.

## 14. Disclaimer

CryptoTrace provides analytical and investigative indicators. It does not independently establish criminal activity, identity, or legal attribution. Ground truth labels are dataset annotations and must be distinguished from the tool's own model prediction.
