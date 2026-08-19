from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.train import train_model

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    metadata = train_model(ROOT / "data" / "processed", ROOT / "models")
    print(json.dumps(metadata["metrics"], indent=2))
