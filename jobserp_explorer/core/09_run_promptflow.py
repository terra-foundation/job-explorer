import subprocess
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import sys
import time

import importlib.util
if not importlib.util.find_spec("promptflow._cli.pf"):
    print("[✗] promptflow._cli.pf module not found in current environment.")
    sys.exit(1)

def run_promptflow_flow(input_path, flow_dir, output_base="outputs/annotated", dry_run=False):
    import shutil
    input_path = Path(input_path).resolve()
    flow_dir = Path(flow_dir).resolve()
    output_base = Path(output_base).resolve()
    output_base.mkdir(parents=True, exist_ok=True)

    # Validate inputs
    if not input_path.exists():
        raise FileNotFoundError(f"[✗] Input file not found: {input_path}")
    if not flow_dir.exists():
        raise FileNotFoundError(f"[✗] Flow directory not found: {flow_dir}")

    flow_name = flow_dir.name
    print(f"[ℹ] Running PromptFlow on: {input_path.name}")
    print(f"[ℹ] Flow directory: {flow_dir}")

    pf_command = [
        str(sys.executable), "-m", "promptflow._cli.pf", "run", "create",
        "--flow", str(flow_dir),
        "--data", str(input_path),
    ]

    print("\n[🔧] Running command:")
    print(" ".join(pf_command))

    if dry_run:
        print("[DRY RUN] Skipping execution.")
        return None

    # Record time before execution
    before_time = datetime.now()

    # Execute
    result = subprocess.run(pf_command, capture_output=True, text=True)

    print("\n[📤] STDOUT:")
    print(result.stdout)
    print("\n[📥] STDERR:")
    print(result.stderr)

    if result.returncode != 0:
        print("[✗] PromptFlow execution failed.")
        sys.exit(1)

    # Sleep briefly to allow filesystem sync
    time.sleep(1)

    # Find most recent .runs folder
    pf_runs_dir = Path.home() / ".promptflow" / ".runs"
    recent_runs = []

    for d in pf_runs_dir.glob(f"{flow_name}_variant_*"):
        mod_time = datetime.fromtimestamp(d.stat().st_mtime)
        if mod_time > before_time - timedelta(seconds=10):
            recent_runs.append((mod_time, d))

    if not recent_runs:
        raise RuntimeError(f"[✗] No recent run dirs found in {pf_runs_dir} for flow `{flow_name}`")

    # Select most recent one
    recent_runs.sort(reverse=True)
    latest_run_dir = recent_runs[0][1]

    print(f"[🗂️] Latest run dir: {latest_run_dir}")

    output_file = latest_run_dir / "outputs.jsonl"
    if not output_file.exists():
        raise RuntimeError(f"[✗] outputs.jsonl not found in {latest_run_dir}")

    # Prepare final output path
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = input_path.stem
    out_path = output_base / f"{stem}_{flow_name}_{timestamp}.jsonl"
    output_base.mkdir(parents=True, exist_ok=True)

    # Copy file
    lines_written = 0
    with open(output_file, "r", encoding="utf-8") as src, open(out_path, "w", encoding="utf-8") as dst:
        for line in src:
            dst.write(line)
            lines_written += 1

    print(f"[✓] Saved {lines_written} lines to: {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--flow_dir", required=True, help="Path to PromptFlow directory")
    parser.add_argument("--output_dir", default="outputs/annotated", help="Directory to save final output")
    parser.add_argument("--dry_run", action="store_true", help="Print the command without executing")
    args = parser.parse_args()

    run_promptflow_flow(args.input, args.flow_dir, output_base=args.output_dir, dry_run=args.dry_run)
