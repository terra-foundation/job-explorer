

import streamlit as st
from pathlib import Path
from run_manager import RunManager
from utils.paths import make_run_dir
import base64
import subprocess
import sys
import os


from jobserp_explorer.config.schema import AppConfig

cfg = AppConfig.from_json(Path("app_config.json"))

# Use config:
output_path = Path(cfg.base_data_dir) / cfg.run_format.format(run_uid="20250710T2000")


def file_download_link(file_or_folder: Path):
    """
    Accept either a file or a folder. If folder, pick most recent file inside.
    """
    if file_or_folder.is_file():
        filepath = file_or_folder
    else:
        candidates = list(file_or_folder.glob("*.jsonl")) + list(file_or_folder.glob("*.csv"))
        if not candidates:
            raise FileNotFoundError(f"No downloadable file found in {file_or_folder}")
        filepath = max(candidates, key=os.path.getmtime)

    with filepath.open("rb") as f:
        data = f.read()

    return st.download_button(
        label=f"📥 Download {filepath.name}",
        data=data,
        file_name=filepath.name
    )

import promptflow

def run_step(script_path, args=None, desc=None):
    from pathlib import Path
    import subprocess
    import sys
    import os

    args = args or []
    cmd = [sys.executable, str(script_path)] + args
    print("Executable:", sys.executable)
    print("sys.path:", sys.path)
    print("promptflow.__file__:", promptflow.__file__)

    # Augment env with current sys.path for safe PYTHONPATH inheritance
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path)

    with st.status(desc or f"Running {Path(script_path).name}", expanded=True) as status:
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env  # ✅ pass custom env
            )
            if result.stdout:
                st.subheader("Standard Output")
                st.code(result.stdout)
            if result.stderr:
                st.subheader("Standard Error")
                st.code(result.stderr)
            if not result.stdout and not result.stderr:
                st.warning("No output captured. Script ran silently.")

            status.update(label="✅ Done", state="complete")

        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error running `{script_path}` (exit code {e.returncode})")

            if e.stdout:
                st.subheader("Standard Output")
                st.code(e.stdout)
            if e.stderr:
                st.subheader("Standard Error")
                st.code(e.stderr)
            if not e.stdout and not e.stderr:
                st.warning("No output captured. The script may have crashed before producing logs.")

            status.update(label="❌ Failed", state="error")

            # Show full traceback if script printed it
            st.subheader("Traceback (from script if any)")
            traceback_text = e.stderr or e.stdout or "No trace available."
            st.code(traceback_text, language="python")


def render():
    st.title("🔧 Pipeline Execution & Observability")

    run_ids = RunManager.list_runs()
    if not run_ids:
        st.warning("No runs found. Please run a query first.")
        return

    run_uid = st.selectbox("Select a run to inspect:", run_ids)
    run = RunManager(run_uid)

    st.markdown(f"### Current Run: `{run_uid}`")

    pipeline_steps = [
        ("scraped_jsonl", "01_serp_scraper.py", "Fetch SERP Results"),
        ("scored_csv", "02_label_and_score.py", "Label & Score Results"),
        ("serp_jsonl_input_dir", "03_export_results_to_jsonl.py", "Prepare PromptFlow Input"),
        ("page_classification_dir", "09_run_promptflow.py", "Classify Page Category", ["--flow_dir", "jobserp_explorer/flow_pagecateg"]),
        ("html_scraped_dir", "05_export_jsonl_with_scraping.py", "Scrape Selected Pages"),
        ("final_scored_jsonl", "09_run_promptflow.py", "Final Match Scoring", ["--flow_dir", "jobserp_explorer/flow_jobposting"]),
    ]



    if st.button("▶ Run All Steps", type="primary"):
        st.info("Running all pipeline steps sequentially...")

        for key, script, label, *opt_args in pipeline_steps:
            st.subheader(f"🔄 {label}")
            args = []

            # ⬇️ Reuse the same argument prep logic from individual buttons
            if key == "scraped_jsonl":
                args = [
                    "--input", str(run.paths["query_csv"]),
                    "--output", str(run.paths["scraped_jsonl"]),
                    "--jsonl_dir", str(run.paths["serp_jsonl_input_dir"]),
                    "--log_dir", str(run.paths["logs"]),
                    "--meta_dir", str(run.paths["metadata"]),
                    "--done_file", str(run.paths["base"] / "done_tracker.csv"),
                ]
            elif key == "scored_csv":
                args = [
                    "--input_dir", str(run.paths["scraped_jsonl"]),
                    "--output_dir", str(run.paths["scored_csv"]),
                    "--log_dir", str(run.paths["logs"]),
                    "--meta_dir", str(run.paths["metadata"]),
                    "--debug"
                ]
            elif key == "serp_jsonl_input_dir":
                args = [
                    "--input_dir", str(run.paths["scored_csv"]),
                    "--output_dir", str(run.paths["serp_jsonl_input_dir"]),
                    "--log_dir", str(run.paths["logs"]),
                    "--meta_dir", str(run.paths["metadata"])
                ]
            elif key == "page_classification_dir":
                input_jsonls = sorted(run.paths["serp_jsonl_input_dir"].glob("*.jsonl"), key=os.path.getmtime)
                if not input_jsonls:
                    st.error("No input JSONL found.")
                    continue
                args = [
                    "--input", str(input_jsonls[-1]),
                    "--output_dir", str(run.paths["page_classification_dir"]),
                ] + opt_args[0]
            elif key == "html_scraped_dir":
                args = [
                    "--input_dir", str(run.paths["scored_csv"]),
                    "--output_dir", str(run.paths["html_scraped_dir"])
                ]
            elif key == "final_scored_jsonl":
                input_jsonls = sorted(run.paths["serp_jsonl_input_dir"].glob("*.jsonl"), key=os.path.getmtime)
                if not input_jsonls:
                    st.error("No JSONL file for final scoring.")
                    continue
                args = [
                    "--input", str(input_jsonls[-1]),
                    "--output_dir", str(run.paths["final_scored_jsonl"]),
                ] + opt_args[0]

            run_step(Path("jobserp_explorer/core") / script, args=args, desc=label)




    for key, script, label, *opt_args in pipeline_steps:
        with st.expander(f"🔹 {label}"):

            output_path = run.paths.get(key)

            # Proper existence check: if key is a directory, check for files inside
            if key in ["serp_jsonl_input_dir", "page_classification_dir", "html_scraped_dir"]:
                exists = output_path.exists() and any(output_path.glob("*"))
            else:
                exists = output_path.exists()


            st.write(f"**Status**: {'✅ Exists' if run.exists(key) else '⏳ Not yet run'}")

            # If there's an actual file or folder, show download link or list
            if exists:
                if output_path.is_file():
                    link = file_download_link(output_path)
                    if link:
                        st.markdown(link, unsafe_allow_html=True)
                elif output_path.is_dir():
                    files = list(output_path.glob("*"))
                    for f in files:
                        if f.is_file():
                            link = file_download_link(f)
                            if link:
                                st.markdown(f"- {link}", unsafe_allow_html=True)




            if st.button(f"▶ Run {label}", key=f"run_{key}"):
                args = []

                if key == "scraped_jsonl":
                    # Step 1: scraper – requires multiple mandatory paths
                    args = [
                        "--input", str(run.paths["query_csv"]),
                        "--output", str(run.paths["scraped_jsonl"]),
                        "--jsonl_dir", str(run.paths["serp_jsonl_input_dir"]),
                        "--log_dir", str(run.paths["logs"]),
                        "--meta_dir", str(run.paths["metadata"]),
                        "--done_file", str(run.paths["base"] / "done_tracker.csv"),
                    ]

                elif key == "scored_csv":
                    args = [
                        "--input_dir", str(run.paths["scraped_jsonl"]),
                        "--output_dir", str(run.paths["scored_csv"]),
                        "--log_dir", str(run.paths["logs"]),
                        "--meta_dir", str(run.paths["metadata"]),
                        "--debug"
                    ]

                elif key == "serp_jsonl_input_dir":
                    args = [
                        "--input_dir", str(run.paths["scored_csv"]),
                        "--output_dir", str(output_path),
                        "--log_dir", str(run.paths["logs"]),
                        "--meta_dir", str(run.paths["metadata"])
                    ]

                elif key == "page_classification_dir":
                    input_jsonls = sorted(run.paths["serp_jsonl_input_dir"].glob("*.jsonl"), key=os.path.getmtime)
                    if not input_jsonls:
                        st.error("No input JSONL found.")
                        continue
                    input_jsonl = input_jsonls[-1]
                    args = [
                        "--input", str(input_jsonl),
                        "--output_dir", str(output_path),
                    ] + opt_args[0]

                elif key == "html_scraped_dir":
                    args = [
                        "--input_dir", str(run.paths["scored_csv"]),
                        "--output_dir", str(output_path)
                    ]

                elif key == "final_scored_jsonl":
                    jsonl_files = sorted(run.paths["serp_jsonl_input_dir"].glob("*.jsonl"), key=os.path.getmtime)
                    if not jsonl_files:
                        st.error("No JSONL file for final scoring.")
                        continue
                    jsonl_input = jsonl_files[-1]
                    args = [
                        "--input", str(jsonl_input),
                        "--output_dir", str(output_path),
                    ] + opt_args[0]

                run_step(Path("jobserp_explorer/core") / script, args=args, desc=label)


if __name__ == "__main__":
    render()
