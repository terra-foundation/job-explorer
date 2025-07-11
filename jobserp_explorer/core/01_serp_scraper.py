import argparse
import hashlib
import html
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

import pandas as pd
import requests
from tqdm import tqdm


# ----------------------------
# Argumentos CLI
# ----------------------------
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, required=True, help='Path to input CSV file')
parser.add_argument('--output', type=str, required=True, help='CSV output file directory')
parser.add_argument('--jsonl_dir', type=str, required=True, help='Directory to store JSONL results')
parser.add_argument('--log_dir', type=str, required=True, help='Directory to store logs')
parser.add_argument('--meta_dir', type=str, required=True, help='Directory to store metadata')
parser.add_argument('--done_file', type=str, required=True, help='Path to CSV tracking done rows')
parser.add_argument('--limit', type=int, help='Limit number of rows processed')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()


SPIDER_API_KEY="sk-f8d1ff52-becc-4414-bb3d-9556fdeb1a36"


# ----------------------------
# Setup de paths y logging
# ----------------------------
root = Path(__file__).resolve().parent.parent
input_path = Path(args.input).resolve()
output_dir = Path(args.output).resolve()
jsonl_dir = Path(args.jsonl_dir).resolve()
log_dir = Path(args.log_dir).resolve()
meta_dir = Path(args.meta_dir).resolve()
done_file = Path(args.done_file).resolve()


for d in [output_dir, jsonl_dir, log_dir, meta_dir]:
    d.mkdir(parents=True, exist_ok=True)

# log_dir = Path(args.log_dir).resolve()
# log_file = log_dir / f'serp_{datetime.now().strftime("%Y%m%dT%H%M%S")}.log'
log_file = log_dir / f'serp.log'
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG if args.debug else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ----------------------------
# Cargar input y registro de completados
# ----------------------------
df = pd.read_csv(input_path)
if args.limit:
    df = df.head(args.limit)

if done_file.exists():
    done_df = pd.read_csv(done_file)
    done_set = set(done_df['query_uid'])
else:
    done_df = pd.DataFrame(columns=['query_uid', 'Job Title', 'Company', 'done_at'])
    done_set = set()


# ----------------------------
# API Spider.cloud
# ----------------------------
SPIDER_API_KEY = os.getenv("SPIDER_API_KEY")
if not SPIDER_API_KEY:
    raise RuntimeError("SPIDER_API_KEY environment variable is not set.")

headers = {
    'Authorization': f'Bearer {SPIDER_API_KEY}',
    'Content-Type': 'application/json',
}



def make_page_uid(serp_url: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(serp_url)).strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()[:10]

def get_serp_results(job_title, company, search_limit=8):
    query = f"{job_title} {company}"
    json_data = {
        "search": query,
        "search_limit": search_limit,
        "return_format": "json"
    }
    try:
        response = requests.post('https://api.spider.cloud/search', headers=headers, json=json_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching results for query '{query}': {e}")
        return []


# ----------------------------
# Proceso principal
# ----------------------------
serp_expanded_rows = []
failed_rows = []

import unicodedata

# def normalize_str(s):
#     return unicodedata.normalize("NFKC", str(s)).strip().lower()

# def make_query_uid(title, company):
#     norm_title = normalize_str(title)
#     norm_company = normalize_str(company)
#     return hashlib.md5(f"{norm_title}|{norm_company}".encode()).hexdigest()[:10]

def make_query_uid(title: str, company: str) -> str:
    norm = lambda s: unicodedata.normalize("NFKC", str(s)).strip().lower()
    return hashlib.md5(f"{norm(title)}|{norm(company)}".encode()).hexdigest()[:10]


for idx, row in tqdm(df.iterrows(), total=len(df)):
    key = f"{row['Job Title']}|{row['Company']}"
    job_company_hash = make_query_uid(row['Job Title'], row['Company'])

    if job_company_hash in done_set:
        logging.info(f"Skipping already processed row: {job_company_hash} — {key}")
        continue

    logging.info(f"[{idx}] Querying: '{key}'")
    results = get_serp_results(row['Job Title'], row['Company'])

    if isinstance(results, dict) and 'content' in results:
        results_list = results['content']
    elif isinstance(results, list):
        results_list = results
    else:
        results_list = []

    logging.info(f"[{idx}] Retrieved {len(results_list)} results")

    # Guardar JSONL
    jsonl_path = jsonl_dir / f'serp_{job_company_hash}.jsonl'
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for result in results_list:
            result['page_uid'] = make_page_uid(result.get('url', ''))
            f.write(json.dumps(result, ensure_ascii=False) + '\n')


    # Agregar a CSV final
    for result in results_list:
        serp_url = result.get('url', '')
        serp_expanded_rows.append({
            'query_uid': job_company_hash,
            'page_uid': make_page_uid(serp_url),
            'job_index': idx,
            'Job Title': row['Job Title'],
            'Company': row['Company'],
            'SERP_title': html.unescape(result.get('title', '')),
            'SERP_description': html.unescape(result.get('description', '')),
            'SERP_url': result.get('url', ''),
            'domain': urlparse(result.get('url', '')).netloc if result.get('url') else ''
        })

    # Marcar como hecho
    done_df = pd.concat([done_df, pd.DataFrame([{
        'query_uid': job_company_hash,
        'Job Title': row['Job Title'],
        'Company': row['Company'],
        'done_at': datetime.now().isoformat()
    }])], ignore_index=True)


# ----------------------------
# Guardado final
# ----------------------------
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
batch_path = output_dir / f'serp_expanded_{timestamp}.csv'
pd.DataFrame(serp_expanded_rows).to_csv(batch_path, index=False)

if done_df.empty:
    print("⚠️ No SERP results to save. Skipping file creation.")
else:
    done_df.to_csv(done_file, index=False)

meta_path = meta_dir / f'serp_meta_{timestamp}.json'
with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump({
        "start_time": datetime.now().isoformat(),
        "n_rows": len(df),
        "n_successful": len(serp_expanded_rows),
        "n_skipped": len(done_set),
        "n_failed": len(failed_rows),
        "failed_indices": failed_rows,
        "output_file": str(batch_path)
    }, f, indent=2)

logging.info(f"Batch completed. Output: {batch_path}")
print(f"✅ Batch completed. {len(serp_expanded_rows)} results saved to {batch_path}")
