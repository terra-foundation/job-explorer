# utils/paths.py
from pathlib import Path


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
