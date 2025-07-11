import argparse
import pandas as pd
import json
from pathlib import Path
from typing import List
from datetime import datetime


def load_llm_outputs(llm_paths: List[Path]) -> pd.DataFrame:
    dfs = []
    for path in llm_paths:
        if not path.exists():
            raise FileNotFoundError(f"LLM file not found: {path}")
        df = pd.read_json(path, lines=True)
        if 'summary' in df.columns:
            summary_df = pd.json_normalize(df['summary'])
            df = pd.concat([df.drop(columns=['summary']), summary_df], axis=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)



def load_scraped(scraped_paths: List[Path]) -> pd.DataFrame:
    dfs = []
    for path in scraped_paths:
        if not path.exists():
            raise FileNotFoundError(f"Scraped file not found: {path}")
        dfs.append(pd.read_json(path, lines=True))
    return pd.concat(dfs, ignore_index=True)


def merge_job_postings(llm_paths: List[Path], scraped_paths: List[Path], output_dir: Path, overwrite=False) -> Path:
    print("📥 Loading LLM outputs...")
    llm_df = load_llm_outputs(llm_paths)
    llm_df = llm_df[llm_df.get("page_type") == "Job Posting"]

    print("📥 Loading scraped HTML data...")
    scraped_df = load_scraped(scraped_paths)

    print("🔗 Merging datasets on `job_index`...")
    merged = llm_df.merge(scraped_df, how='left', on='job_index', suffixes=('', '_scraped'))
    merged.drop(columns=[col for col in merged.columns if col.startswith('line_number')], errors='ignore', inplace=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{datetime.today().strftime('%Y%m%d')}_job_postings_merged.jsonl"

    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {out_path} (use --overwrite to allow)")

    print(f"💾 Writing output to {out_path}...")
    with open(out_path, 'w', encoding='utf-8') as f:
        for record in merged.to_dict(orient='records'):
            json.dump(record, f, ensure_ascii=False)
            f.write('\n')

    print(f"✅ Done. Merged file: {out_path}")
    return out_path



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LLM outputs with scraped HTML job data.")
    parser.add_argument("--llm", nargs="+", required=True, help="Paths to LLM .jsonl files")
    parser.add_argument("--scraped", nargs="+", required=True, help="Paths to scraped .jsonl files")
    parser.add_argument("--output_dir", required=True, help="Directory to save merged output")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite if output already exists")

    args = parser.parse_args()

    llm_paths = [Path(p) for p in args.llm]
    scraped_paths = [Path(p) for p in args.scraped]
    output_dir = Path(args.output_dir)

    merge_job_postings(llm_paths, scraped_paths, output_dir, args.overwrite)
