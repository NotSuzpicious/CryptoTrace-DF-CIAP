from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.model_manager import ModelManager

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    manager = ModelManager(ROOT / "models")
    if not manager.metadata:
        raise SystemExit("Model metadata not found. Run prepare_dataset.py and train_model.py first.")
    print(json.dumps(manager.metadata["metrics"], indent=2))
