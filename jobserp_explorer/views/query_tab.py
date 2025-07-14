
import streamlit as st
import subprocess
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import os
from run_manager import RunManager
from utils.paths import make_run_dir


from jobserp_explorer.config.schema import AppConfig

cfg = AppConfig.from_json(Path("app_config.json"))

# Use config:
output_path = Path(cfg.base_data_dir) / cfg.run_format.format(run_uid="20250710T2000")

import promptflow

def run_step(script_path, args=None, desc=None):
    from pathlib import Path
    import subprocess
    import sys

    args = args or []

    # Ensure absolute path from repo root
    REPO_ROOT = Path(__file__).resolve().parents[2]
    full_script_path = REPO_ROOT / script_path

    cmd = [sys.executable, str(full_script_path)] + args

    # ✅ Define custom env
    env = os.environ.copy()
    env["PYTHON_KEYRING_BACKEND"] = "keyrings.alt.file.PlaintextKeyring"
    env["PYTHONPATH"] = ":".join(sys.path)

    print("Executable:", sys.executable)
    print("sys.path:", sys.path)
    print("promptflow.__file__:", promptflow.__file__)

    with st.status(desc or f"Running {Path(script_path).name}", expanded=True) as status:
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env  # ✅ critical fix
            )
            st.code(result.stdout)
            status.update(label="✅ Done", state="complete")
        except subprocess.CalledProcessError as e:
            st.error(f"Error running {script_path}")
            if e.stdout:
                st.subheader("Standard Output")
                st.code(e.stdout)
            if e.stderr:
                st.subheader("Standard Error")
                st.code(e.stderr)
            status.update(label="❌ Failed", state="error")
            st.subheader("Traceback (from script if any)")
            traceback_text = e.stderr or e.stdout or "No trace available."
            st.code(traceback_text, language="python")

def run_remotive_fetch(query: str, location: str, limit: int, output_path: Path) -> Path:
    search_term = query.strip()
    # if location.strip():  # Breaks the search
    #     print('search_term: ', search_term)
    #     search_term += f" {location.strip()}"


    cmd = [
        sys.executable,
        "jobserp_explorer/core/00_fetch_remotive_jobs.py",
        "--query", search_term,
        "--limit", str(limit),
        "--output", str(output_path)
    ]
    try:
        result = subprocess.run(cmd, check=True, text=True)
        st.info(result.stdout)
        return output_path
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to fetch jobs from Remotive:\n\n{e.stderr}")
        return None

def run_pipeline_with_uid(run_uid: str, limit = None):

    args = [
        "--run_uid", run_uid
    ]

    if limit is not None:
        args += ["--limit", str(limit)]

    return run_step(
        script_path="jobserp_explorer/core/10_run_full_pipeline.py",
        args=args,
        desc="Running full pipeline"
    )


# def run_pipeline_with_uid(run_uid: str):
#     script_path = Path("jobserp_explorer/core/10_run_full_pipeline.py").resolve()
#     cmd = [
#         sys.executable,
#         str(script_path),
#         "--run_uid", run_uid
#     ]
#     result = subprocess.run(cmd, text=True)
#     if result.returncode != 0:
#         raise RuntimeError(f"Pipeline failed:\n{result.stderr}")
#     return result.stdout

from datetime import datetime

def render():
    st.header("🔍 Search Jobs")

    st.subheader("New Job Query")
    with st.form("query_form"):

        search_term = st.text_input("Job Title", placeholder="e.g. Data Scientist",
                                    key="search_term")
        location = st.text_input("Location (optional)", placeholder="e.g. Remote",
                                key="location")
        result_limit = st.slider("Number of Results", min_value=1, max_value=50, value=2,
                                key="result_limit")
                                
        auto_run = st.checkbox("Run full pipeline after search", value=True)
        submitted = st.form_submit_button("Start Search")

    if submitted:
        if not search_term.strip():
            st.error("Search term cannot be empty.")
            return

        run_uid = datetime.now().strftime("%Y%m%dT%H%M%S")
        run = RunManager(run_uid)

        run.save_metadata({
            "query": search_term,
            "location": location,
            "timestamp": run_uid
        }, overwrite=False)

        output_path = run.paths["query_csv"]
        jobs_csv = run_remotive_fetch(search_term, location, result_limit, output_path)

        if not jobs_csv or not jobs_csv.exists():
            st.error("No results or failed query.")
            return

        st.session_state["last_run_uid"] = run_uid
        st.success(f"🎯 Run `{run_uid}` created for: '{search_term}' ({location})")

        try:
            df_jobs = pd.read_csv(jobs_csv)
            if not df_jobs.empty:
                st.markdown("**🔎 Preview of fetched results:**")
                st.dataframe(df_jobs.head(15), use_container_width=True)
        except Exception as e:
            st.warning(f"Could not load preview: {e}")

        if auto_run:
            with st.spinner("Running full pipeline..."):
                try:
                    output = run_pipeline_with_uid(run_uid, limit = result_limit)
                    st.success("✅ Pipeline completed successfully.")
                except Exception as e:
                    st.error(str(e))

        st.markdown("---")
        st.markdown("### 🕒 Recent Runs")
        for uid in RunManager.list_runs()[:5]:

            try:
                meta = RunManager(uid).query_metadata()
                label = f"{meta.get('query', '?')} ({meta.get('location', '-')}) — {meta.get('timestamp', '')}"
            except FileNotFoundError:
                label = f"[Missing meta] — {uid}"

            if st.button(label, key=f"resume_{uid}"):
                st.session_state["last_run_uid"] = uid
                st.success(f"Resumed run `{uid}`. Check progress tab.")
