import argparse
import subprocess
import sys
from pathlib import Path
import os

# from utils.paths import make_run_dir

# sys.path.append('./../')
sys.path.append('./')

from jobserp_explorer.run_manager import *

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


def run_command(cmd, desc=None):
    print(f"\n[↪] {desc or 'Running'}:\n{' '.join(str(x) for x in cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[✗] {desc or 'Command failed'}")
        sys.exit(1)
    print(f"[✓] {desc or 'Done'}")

import json
from datetime import datetime

def main(query=None, input_csv=None, run_uid=None):
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    if not run_uid:
        run_uid = timestamp  # fallback if none passed

    paths = make_run_dir(run_uid)
    Path(paths["base"]).mkdir(parents=True, exist_ok=True)
    Path(paths["logs"]).mkdir(parents=True, exist_ok=True)


    metadata_path = paths["metadata"] / "meta.json"
    paths["metadata"].mkdir(parents=True, exist_ok=True)

    with open(metadata_path, "w") as f:
        json.dump({
            "run_uid": run_uid,
            "query": query,
            "input_csv": str(input_csv),
            "timestamp": timestamp
        }, f, indent=2)


    # === STEP 00: Fetch from Remotive if query provided ===
    if query:
        print(f"[↪] Step 00: Query Remotive for jobs matching '{query}'")

        # jobs_dir = Path("data/00_query_jobs")
        # jobs_dir.mkdir(parents=True, exist_ok=True)
        input_csv = paths["query_csv"]

        run_command([
            sys.executable, "jobserp_explorer/core/00_fetch_remotive_jobs.py",
            "--query", query,
            "--limit", "3",
            "--output", str(input_csv)
        ], desc="Step 00: Fetch from Remotive")

    # elif input_csv:
    #     input_csv = Path(input_csv).resolve()
    #     if not input_csv.exists():
    #         print(f"[✗] Provided input file does not exist: {input_csv}")
    #         sys.exit(1)
    else:
        print("[✗] No query provided.")
        sys.exit(1)

    print(f"[ℹ] Starting full pipeline for: {input_csv}")
    base_name = Path(input_csv).stem
    run_id = f"{base_name}_{timestamp}"

    # === STEP 01: Fetch SERPs ===
    # step00 = Path("data/01_fetch_serps")
    serp_raw_dir = paths["scraped_jsonl"]
    jsonl_serp_dir = paths["scraped_jsonl"]
    logs_serp_dir = paths["logs"]
    metadata = paths["metadata"]
    done_file_serp = paths["base"] / "done_tracker.csv"

    run_command([
        sys.executable, "jobserp_explorer/core/01_serp_scraper.py",
        "--input", str(input_csv),
        "--output", str(serp_raw_dir),
        "--jsonl_dir", str(jsonl_serp_dir),
        "--log_dir", str(logs_serp_dir),
        "--meta_dir", str(metadata),
        "--done_file", str(done_file_serp)
    ], desc="Step 0: Fetch SERPs")

    # === STEP 01: Label + Score ===
    # step01 = Path("data/02_label_score")
    logs_scores_dir = paths["logs"]
    results_scored = paths["scored_csv"]
    meta_scores_dir = paths["metadata"]

    run_command([
        sys.executable, "jobserp_explorer/core/02_label_and_score.py",
        "--input_dir", str(serp_raw_dir),
        "--output_dir", str(results_scored),
        "--log_dir", str(logs_scores_dir),
        "--meta_dir", str(meta_scores_dir),
        "--debug"  # Optional: only add this if you're debugging
    ], desc="Step 2: Label and score results")

    # === STEP 02: Export JSONL for PromptFlow Classification ===
    # step02 = Path("data/03_serp_class_input")
    jsonl_input_dir = paths["serp_jsonl_input_dir"]
    meta_jsonl_dir = paths["metadata"]
    log_jsonl_dir = paths["logs"]

    run_command([
        sys.executable, "jobserp_explorer/core/03_export_results_to_jsonl.py",
        "--input_dir", str(results_scored),
        "--output_dir", str(jsonl_input_dir),
        "--meta_dir", str(meta_jsonl_dir),
        "--log_dir", str(log_jsonl_dir)
    ])

    jsonl_candidates = sorted(jsonl_input_dir.glob("serp_class_input_*.jsonl"), key=os.path.getmtime, reverse=True)
    
    if not jsonl_candidates:
        print("[✗] No JSONL file found in", jsonl_input_dir)
        sys.exit(1)
    jsonl_path = jsonl_candidates[0]

    # === STEP 03: PromptFlow - Page Classification ===


    # step04 = Path("data/04_scraped_html")
    html_scraped = paths["html_scraped_dir"]

    # step06 = Path("data/06_jobposting_finalmatch")
    jsonl_finalannot = 	paths["final_scored_jsonl"]


    run_command([
        sys.executable, "jobserp_explorer/core/09_run_promptflow.py",
        "--input", str(jsonl_path),
        "--flow_dir", "jobserp_explorer/flow_pagecateg",
        "--output_dir", paths["page_classification_dir"]
    ], desc="Step 2: Run SERP-based page classification")


    # Step 4: Scrape selected pages with Selenium
    run_command([
        sys.executable, "jobserp_explorer/core/05_export_jsonl_with_scraping.py",
        "--input_dir", str(results_scored),
        "--output_dir", str(html_scraped)
    ], desc="Step 4: Scrape top SERP pages")

    # Step 6: Run PromptFlow for final match scoring
    # Select most recent JSONL
    jsonl_files = sorted(paths["serp_jsonl_input_dir"].glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    if not jsonl_files:
        print("[✗] No JSONL file found in", jsonl_input_dir)
        sys.exit(1)
    jsonl_input = str(jsonl_files[0])
    print(f"[✓] Found JSONL file: {jsonl_input}")

    run_command([
        sys.executable, "jobserp_explorer/core/09_run_promptflow.py",
        "--input", jsonl_input,
        "--flow_dir", "jobserp_explorer/flow_jobposting",
        "--output_dir", str(jsonl_finalannot)
    ], desc="Step 6: Run final PromptFlow (match relevance)")

    print(f"[🏁] Pipeline complete for: {run_uid}")
# /home/matias/repos/jobserp_explorer/jobserp_explorer/run_manager.py

if __name__ == "__main__":
    import argparse
    import sys
    from jobserp_explorer.run_manager import RunManager

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Search query for Remotive")
    parser.add_argument("--input_csv", type=str, help="Optional CSV file path")
    parser.add_argument("--run_uid", type=str, required=True, help="Run UID (e.g., 20250710T140520)")
    args = parser.parse_args()

    run = RunManager(args.run_uid)
    meta = run.query_metadata()

    query = args.query or meta.get("query")
    input_csv = args.input_csv or run.paths.get("query_csv")

    if not query:
        print(f"[✗] Missing query. Neither CLI nor metadata had it.")
        sys.exit(1)

    if not input_csv or not Path(input_csv).exists():
        print(f"[✗] Input CSV not found at: {input_csv}")
        sys.exit(1)

    print(f"[⏱] Running pipeline for: {args.run_uid}")
    print(f"[📂] Metadata path: {run.metadata_file}")
    print(f"[📥] Using input CSV: {input_csv}")

    # Launch main
    main(query=query, input_csv=input_csv, run_uid=args.run_uid)
