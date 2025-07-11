import os
import glob
import html
import argparse
import pandas as pd
from urllib.parse import urlparse
from pathlib import Path


# %%
# Known ATS Providers
ats_providers_scored = { 
    'greenhouse.io': ('ATS', 3),
    'lever.co': ('ATS', 3),
    'workable.com': ('ATS', 3),
    'breezy.hr': ('ATS', 2),
    'personio.com': ('ATS', 2),
    'personio.de': ('ATS', 2),
    'comeet.com': ('ATS', 2),
    'careers-page.com': ('ATS', 1),
    'freshteam.com': ('ATS', 1)
}

# Aggregator or Job Board
aggregators_scored = {
    'linkedin.com': ('Aggregator_T1', 2),
    'indeed.com': ('Aggregator_T1', 2),
    'glassdoor.com': ('Aggregator_T1', 2),
    'ziprecruiter.com': ('Aggregator_T1', 2),
    
    'wellfound.com': ('Aggregator_T2', 1),
    'remoterocketship': ('Aggregator_T2', 1),
    'builtin.com': ('Aggregator_T2', 1),
    'stepstone.de': ('Aggregator_T2', 1),
    'remotive.com': ('Aggregator_T2', 1),
    'weworkremotely.com': ('Aggregator_T2', 1),

    'reddit.com': ('Aggregator_T3', 0),
    'remoteok.com': ('Aggregator_T3', 0),
    'dailyremote.com': ('Aggregator_T3', 0),
    'himalayas.app': ('Aggregator_T3', 0),
    'grabjobs.co': ('Aggregator_T3', 0),
    'jobgether.com': ('Aggregator_T3', 0),
    'rubyonremote.com': ('Aggregator_T3', 0),
    'gohire.io': ('Aggregator_T3', 0),
    'jobot.com': ('Aggregator_T3', 0),
    'virtualvocations.com': ('Aggregator_T3', 0),
    'fullstack.com': ('Aggregator_T3', 0),
    'dice.com': ('Aggregator_T3', 0),
    'otta.com': ('Aggregator_T3', 0),
    'lensa.com': ('Aggregator_T3', 0),
    'uplers.com': ('Aggregator_T3', 0),
    'levels.fyi': ('Aggregator_T3', 0),
    'cherry.vc': ('Aggregator_T3', 0),
    'datacareer.de': ('Aggregator_T3', 0),
    'theorg.com': ('Aggregator_T3', 0)
}

# --- Core Functions ---
def extract_domain_from_url(url):
    if pd.isnull(url):
        return ''
    return urlparse(url).netloc.lower()

import unicodedata, hashlib

def make_query_uid(title: str, company: str) -> str:
    norm = lambda s: unicodedata.normalize("NFKC", str(s)).strip().lower()
    return hashlib.md5(f"{norm(title)}|{norm(company)}".encode()).hexdigest()[:10]

def make_page_uid(serp_url: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(serp_url)).strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()[:10]


def label_and_score(row):
    domain = row.get('domain', '').lower()
    company = str(row.get('company', '')).lower()
    if company and company in domain:
        return ('Employer', 2.5)
    for k, v in ats_providers_scored.items():
        if k in domain:
            return v
    for k, v in aggregators_scored.items():
        if k in domain:
            return v
    return ('Unknown', 0)


def label_and_score(row, ats_providers_scored, aggregators_scored):
    domain = str(row['domain']).lower()
    company = str(row['company']).lower()

    if company in domain:
        return ('Employer', 2.5)

    for key in ats_providers_scored:
        if key in domain:
            return ('ATS', ats_providers_scored[key][1])
    
    for key in aggregators_scored:
        if key in domain:
            return (aggregators_scored[key][0], aggregators_scored[key][1])
    
    return ('Unknown', 0)


def filter_top_candidates(df, n_per_label=2, n_unknown=1, group_key='job_index', score_col='score'):
    """
    Filters top candidates by score per label and job_index.

    Parameters:
    - df: Input DataFrame with 'label', 'score', and grouping columns.
    - n_per_label: Max number of entries to keep per label type per group.
    - n_unknown: Max number of 'Unknown' entries to keep per group.
    - group_key: Column to group by (e.g., 'job_index' or 'query_uid').
    - score_col: Column to sort within each group.

    Returns:
    - Filtered DataFrame with capped entries per group/label.
    """
    # Keep top N per label (e.g. Employer, ATS)
    label_filter = df['label'].isin(['Employer', 'ATS'])
    top_known = (
        df[label_filter]
        .groupby([group_key, 'label'], group_keys=False)
        .apply(lambda g: g.sort_values(by=score_col, ascending=False).head(n_per_label))
    )

    # Keep top N Unknown per group
    top_unknown = (
        df[df['label'] == 'Unknown']
        .groupby(group_key, group_keys=False)
        .apply(lambda g: g.sort_values(by=score_col, ascending=False).head(n_unknown))
    )

    return (
        pd.concat([top_known, top_unknown])
        .sort_values(by=[group_key, score_col], ascending=[True, False])
        .reset_index(drop=True)
    )


def save_results_csv(df, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')



# === Main Pipeline Logic ===
import logging
import json
from datetime import datetime

def main(input_dir, output_dir, log_dir, meta_dir, debug=False):
    input_files = glob.glob(os.path.join(input_dir, 'serp_expanded_*.csv'))
    logging.info(f"Found {len(input_files)} input files.")

    for input_file in input_files:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filtered = os.path.join(output_dir, f"{base_name}_results.csv")
        output_full = os.path.join(output_dir, f"{base_name}_scored_full.csv")
        meta_path = os.path.join(meta_dir, f"{base_name}_meta.json")

        if os.path.exists(output_filtered):
            logging.info(f"[SKIP] {base_name} already processed.")
            continue

        logging.info(f"[PROCESS] {base_name}")
        try:
            df = pd.read_csv(input_file, encoding='utf-8')
        except pd.errors.EmptyDataError:
            logging.warning(f"[SKIP] {input_file} is empty or corrupt.")
            continue

        # Normalize early
        df = df.rename(columns={
            "Job Title": "job_title",
            "Company": "company",
            "SERP_title": "serp_title",
            "SERP_description": "serp_description",
            "SERP_url": "serp_url"
        })
        

        if 'domain' not in df.columns or df['domain'].isnull().all():
            df['domain'] = df['serp_url'].apply(extract_domain_from_url)
        else:
            df['domain'] = df['domain'].fillna('').apply(str).str.lower()


        df['serp_title'] = df['serp_title'].apply(lambda x: html.unescape(str(x)))
        df['serp_description'] = df['serp_description'].apply(lambda x: html.unescape(str(x)))

        df['query_uid'] = df.apply(lambda row: make_query_uid(row['job_title'], row['company']), axis=1)
        df['page_uid'] = df['serp_url'].apply(make_page_uid)

        df[['label', 'score']] = df.apply(
            lambda row: label_and_score(row, ats_providers_scored, aggregators_scored),
            axis=1, result_type='expand'
        )

        # Save full scored version for audit
        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(output_full, index=False, encoding='utf-8')
        logging.info(f"[SAVE] Full scored CSV → {output_full}")

        # Filtering
        filtered = filter_top_candidates(df, n_per_label=2, n_unknown=1)

        filtered['google_search'] = filtered.apply(
            lambda row: f"https://www.google.com/search?q=site:{row['domain']}+{row['job_title']}+{row['company']}+{row['serp_title']}",
            axis=1
        )

        final_cols = [
            'query_uid', 'page_uid', 'job_index', 'job_title', 'company',
            'serp_title', 'domain', 'label', 'score', 'serp_url', 'google_search'
        ]
        save_results_csv(filtered[final_cols], output_filtered)
        logging.info(f"[SAVE] Filtered results → {output_filtered}")

        # Metadata logging
        meta = {
            "file": base_name,
            "timestamp": datetime.now().isoformat(),
            "n_input": len(df),
            "n_filtered": len(filtered),
            "label_distribution": df['label'].value_counts().to_dict(),
            "n_unique_queries": df['query_uid'].nunique(),
            "n_unique_pages": df['page_uid'].nunique()
        }
        os.makedirs(meta_dir, exist_ok=True)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
        logging.info(f"[META] Metadata saved → {meta_path}")

        
# === CLI Entry Point ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True, help="Input directory with expanded SERP CSVs")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory to save labeled results")
    parser.add_argument('--log_dir', type=str, required=True, help='Directory to store logs')
    parser.add_argument("--meta_dir", type=str, required=True)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()
    log_dir = Path(args.log_dir).resolve()
    # log_file = log_dir / f'serp_label_score_{datetime.now().strftime("%Y%m%dT%H%M%S")}.log"
    log_file = log_dir / f'serp_label_score.log'
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    main(args.input_dir, args.output_dir, args.log_dir, args.meta_dir, args.debug)