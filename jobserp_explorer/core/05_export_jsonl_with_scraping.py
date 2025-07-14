import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
import glob

load_dotenv()

SPIDER_API_KEY = os.getenv("SPIDER_API_KEY")
if not SPIDER_API_KEY:
    raise RuntimeError("Missing SPIDER_API_KEY in environment")

HEADERS = {
    "Authorization": f"Bearer {SPIDER_API_KEY}",
    "Content-Type": "application/json",
}

def scrape_url(url: str, return_format="markdown", readability=True,
               clean_html=True, filter_output_main_only=True, retries=2, delay=1.5):
    payload = {
        "url": url,
        "return_format": return_format,
        "readability": readability,
        "clean_html": clean_html,
        "filter_output_main_only": filter_output_main_only
    }

    for attempt in range(retries + 1):
        try:
            response = requests.post("https://api.spider.cloud/scrape", headers=HEADERS, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data and "content" in data[0]:
                return data[0]["content"]
            return ""
        except Exception as e:
            if attempt < retries:
                print(f"[!] Retry ({attempt+1}) for {url} due to error: {e}")
                time.sleep(delay)
            else:
                print(f"[✗] Failed after {retries+1} attempts: {url}")
                return None

import pandas as pd
from tqdm import tqdm

def process_file(input_csv: Path, output_dir: Path, **scrape_opts):
    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_jsonl = output_dir / f"{base_name}_spider_scraped.jsonl"


    df = pd.read_csv(input_csv)
    if df.empty:
        print(f"[✗] Empty file: {input_csv}")
        return

    df.columns = [c.lower().strip() for c in df.columns]
    if "serp_url" not in df.columns:
        raise ValueError("Missing `serp_url` column in input CSV.")

    output_rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Scraping pages"):
        url = row.get("serp_url")
        if not url:
            continue

        content = scrape_url(url, **scrape_opts)
        output_rows.append({
            "query_uid": row.get("query_uid"),
            "page_uid": row.get("page_uid"),
            "job_index": row.get("job_index"),
            "job_title": row.get("job_title"),
            "company": row.get("company"),
            "label": row.get("label"),
            "score": row.get("score"),
            "domain": row.get("domain"),
            "serp_url": url,
            "serp_title": row.get("serp_title"),
            "google_search": row.get("google_search"),
            "scraped_data": content
        })

    with open(output_jsonl, "w", encoding="utf-8") as f:
        for entry in output_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[✓] Saved: {output_jsonl}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, help="Directory with input CSV files")
    parser.add_argument("--output_dir", required=True, help="Directory to write output files")
    parser.add_argument("--format", default="markdown", choices=["markdown", "text", "html"], help="Return format")
    parser.add_argument("--readability", action="store_true", help="Use readability mode")
    parser.add_argument("--no-readability", dest="readability", action="store_false")
    parser.set_defaults(readability=True)
    parser.add_argument("--clean_html", action="store_true")
    parser.set_defaults(clean_html=True)
    parser.add_argument("--main_only", action="store_true")
    parser.set_defaults(main_only=True)

    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Match files like: serp_expanded_20250713T214212_results.csv
    print(f"🔍 Scanning directory: {input_dir}")
    input_files = sorted(glob.glob(os.path.join(input_dir, "serp_expanded_*_results.csv")), key=os.path.getmtime, reverse=True)

    if not input_files:
        print(f"[✗] No matching CSV files found in {input_dir}.")
        sys.exit(1)


    for csv_path in input_files:
        print(f"[→] Processing: {csv_path}")
        process_file(
            csv_path,
            output_dir=output_dir,
            return_format=args.format,
            readability=args.readability,
            clean_html=args.clean_html,
            filter_output_main_only=args.main_only
        )