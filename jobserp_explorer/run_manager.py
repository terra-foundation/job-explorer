from pathlib import Path
import json
from datetime import datetime
import sys

sys.path.append('./')


def make_run_dir(run_uid: str) -> dict:
    base = Path(f"data/01_fetch_serps/run_{run_uid}")
    return {
        "base": base,
        "query_csv": base / "00_query",
        "scraped_jsonl": base / "01_scraped",
        "classified_jsonl": base / "02_classified",
        "scored_csv": base / "03_scored",
        "serp_jsonl_input_dir": base / "04_serp_jsonl_input",
        "page_classification_dir": base / "05_page_classification/00_jsonl_annotated",
        "html_scraped_dir": base / "06_scraped_html",
        "final_scored_jsonl": base / "07_final_scored",
        "logs": base / "logs",
        "metadata": base / "metadata",
    }



class RunManager:
    BASE_DIR = Path("data/01_fetch_serps")

    def __init__(self, run_uid: str):
        self.run_uid = run_uid
        self.paths = make_run_dir(run_uid)
        self.run_dir = self.paths["base"]
        self.metadata_dir = self.paths.get("metadata", self.run_dir / "metadata")
        self.metadata_file = self.metadata_dir / "meta.json"

    def exists(self, step: str) -> bool:
        return self.paths.get(step, Path("_")).exists()

    def read_log(self, step: str) -> str:
        log_path = self.paths["logs"] / f"{step}.log"
        if log_path.exists():
            return log_path.read_text()
        return "No log available."

    def get_output(self, step: str):
        path = self.paths.get(step)
        if path and path.exists():
            if path.suffix == ".jsonl":
                return [json.loads(line) for line in path.open()]
            elif path.suffix == ".csv":
                import pandas as pd
                return pd.read_csv(path)
        return None

    def query_metadata(self) -> dict:
        if self.metadata_file.exists():
            try:
                return json.load(self.metadata_file.open())
            except Exception:
                return {}
        return {}

    def save_metadata(self, metadata: dict, overwrite: bool = False):
        # 🛠 Ensure metadata directory exists
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        current = self.query_metadata()

        if not overwrite:
            # Only update fields that aren't set or are None
            current.update({k: v for k, v in metadata.items() if k not in current or current[k] is None})
        else:
            current.update(metadata)

        with self.metadata_file.open("w") as f:
            json.dump(current, f, indent=2)



    @staticmethod
    def list_runs():
        all_runs = sorted(RunManager.BASE_DIR.glob("run_*"), reverse=True)
        return [r.name.replace("run_", "") for r in all_runs]
