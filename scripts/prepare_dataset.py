from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.preprocessing import prepare_dataset, summarize_dataset

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    summary = summarize_dataset(ROOT)
    result = prepare_dataset(ROOT, ROOT / "data" / "processed", ROOT / "data" / "demo")
    print(json.dumps({"summary": summary.__dict__, "split": result}, indent=2))
