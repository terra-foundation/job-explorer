from pathlib import Path
import pandas as pd
import json
import os
import glob
import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input_dir", required=True)
parser.add_argument("--output_dir", required=True)
args = parser.parse_args()

input_dir = Path(args.input_dir).resolve()
output_dir = Path(args.output_dir).resolve()
output_dir.mkdir(parents=True, exist_ok=True)



print(f"Scanning directory: {input_dir}")
input_files = glob.glob(os.path.join(input_dir, 'serp_expanded_*_results.csv'))
if not input_files:
    print(f"[WARN] No CSV files found in {input_dir}. Skipping JSONL export.")
    exit()

def scrape_and_return_html(driver, url, sleep_time=5):
    try:
        driver.get(url)
        time.sleep(sleep_time)
        body = driver.find_element("tag name", "body")
        body.send_keys(Keys.CONTROL, 'a')
        body.send_keys(Keys.CONTROL, 'c')
        time.sleep(1)
        return pyperclip.paste()
    except Exception as e:
        print(f"[ERROR] Failed to scrape: {url}\n{e}")
        return ""

def process_file(csv_file, driver):
    df = pd.read_csv(csv_file, encoding="utf-8")
    if df.empty:
        print(f"[SKIP] {csv_file} is empty.")
        return

    print(f"[INFO] Loaded {len(df)} rows from {csv_file}")
    print("Columns:", list(df.columns))

    # Determine output path
    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    jsonl_file = output_dir / f"{base_name}.jsonl"

    if jsonl_file.exists():
        print(f"[✓] Found existing JSONL file: {jsonl_file}, skipping.")
        return

    # Normalize column names (in case source used camelCase)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Scraping {base_name}"):
        scraped_html = scrape_and_return_html(driver, row['serp_url'])
        row_dict = {
            "job_index": row.get("job_index"),
            "job_title": row.get("job_title"),
            "company": row.get("company"),
            "label": row.get("label"),
            "score": row.get("score"),
            "domain": row.get("domain"),
            "serp_url": row.get("serp_url"),
            "serp_title": row.get("serp_title", None),
            "google_search": row.get("google_search", None),
            "scraped_data": scraped_html
        }
        rows.append(row_dict)

    # Write final JSONL
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for r in rows:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")

    print(f"[✓] Saved scraped JSONL to: {jsonl_file}")

# Setup Selenium driver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

# Process each file
for csv_file in input_files:
    process_file(csv_file, driver)

driver.quit()
