import argparse
import os
import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import unicodedata
import hashlib

# === UID Utility ===
def normalize_str(s):
    return unicodedata.normalize("NFKC", str(s)).strip().lower()

def make_query_uid(title: str, company: str) -> str:
    return hashlib.md5(f"{normalize_str(title)}|{normalize_str(company)}".encode()).hexdigest()[:10]


def make_page_uid(serp_url: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(serp_url)).strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()[:10]

# === Export Function ===
def export_jsonl(input_dir, output_dir, meta_dir, log_dir, debug=False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    meta_dir = Path(meta_dir)
    log_dir = Path(log_dir)

    for d in [output_dir, meta_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f'export_jsonl_{datetime.now().strftime("%Y%m%dT%H%M%S")}.log'
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    input_files = sorted(input_dir.glob("*_results.csv"))
    logging.info(f"Found {len(input_files)} result files.")

    all_rows = []
    for file in input_files:
        logging.info(f"[READ] {file.name}")
        try:
            df = pd.read_csv(file)
        except pd.errors.EmptyDataError:
            logging.warning(f"[SKIP] Empty file: {file}")
            continue

        for row in df.itertuples(index=False):
            row_dict = {
                "job_index": row.job_index,
                "query_uid": make_query_uid(row.job_title, row.company),
                "job_title": row.job_title,
                "company": row.company,
                "page_uid": make_page_uid(row.serp_url),
                "serp_url": row.serp_url,
                "scraped_data": ""
            }
            all_rows.append(row_dict)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_path = output_dir / f"serp_class_input_{timestamp}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            json.dump(row, f)
            f.write("\n")

    logging.info(f"[EXPORT] {len(all_rows)} records to {out_path}")

    # Metadata sidecar
    meta = {
        "timestamp": timestamp,
        "n_files": len(input_files),
        "n_records": len(all_rows),
        "output_file": str(out_path)
    }
    meta_path = meta_dir / f"serp_class_input_{timestamp}.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    logging.info(f"[META] Metadata saved → {meta_path}")

    print(f"[✓] Exported {len(all_rows)} entries to {out_path}")
    return out_path

# === CLI Entry Point ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--meta_dir", required=True)
    parser.add_argument("--log_dir", required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    export_jsonl(args.input_dir, args.output_dir, args.meta_dir, args.log_dir, args.debug)
