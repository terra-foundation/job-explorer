#!/usr/bin/env python

import argparse

import pandas as pd
from pathlib import Path


try:
    import requests
except ModuleNotFoundError:
    import sys
    print("❌ Required dependency 'requests' not found. Are you running before installation finished?", file=sys.stderr)
    sys.exit(1)


def fetch_remotive_jobs(query: str, limit: int = 50) -> pd.DataFrame:
    """
    Fetch jobs from Remotive API based on a search term.
    Returns a DataFrame with standardized columns.
    """
    endpoint = "https://remotive.com/api/remote-jobs"
    params = {"search": query, "limit": limit}
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])

    df = pd.DataFrame([{
        "Job Title": job["title"],
        "Company": job["company_name"],
        "Location": job["candidate_required_location"],
        # "Job URL": job["url"]
    } for job in jobs])

    return df

def main():
    parser = argparse.ArgumentParser(description="Fetch jobs from Remotive API and save as CSV.")
    parser.add_argument("--query", type=str, required=True, help="Search term for job query, e.g., 'data science'")
    parser.add_argument("--limit", type=int, default=50, help="Max number of results to fetch (default: 50)")
    parser.add_argument("--output", type=str, default="00_input/jobs_from_query.csv", help="Output CSV file path")

    args = parser.parse_args()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[→] Fetching Remotive jobs for: '{args.query}' (limit: {args.limit})")
    df = fetch_remotive_jobs(args.query, args.limit)

    if df.empty:
        print("[!] No jobs found.")
    else:
        df.to_csv(output_path, index=False)
        print(f"[✓] Saved {len(df)} jobs to: {output_path}")

if __name__ == "__main__":
    main()
