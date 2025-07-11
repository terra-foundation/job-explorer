
from pathlib import Path
import streamlit as st
import json
import pandas as pd


from jobserp_explorer.config.schema import AppConfig

cfg = AppConfig.from_json(Path("app_config.json"))

# Use config:
output_path = Path(cfg.base_data_dir) / cfg.run_format.format(run_uid="20250710T2000")


from jobserp_explorer.config.paths import DATA_DIR
BASE_DIR = DATA_DIR


def load_jsonl(path):
    with open(path, "r") as f:
        return [json.loads(line.strip()) for line in f.readlines()]

def render():
    st.header("📊 Job Match Results")

    # === Step 1: List runs ===
    run_dirs = sorted([p for p in BASE_DIR.glob("run_*") if p.is_dir()], reverse=True)
    if not run_dirs:
        st.error("No run directories found.")
        return

    selected_run = st.selectbox("Select a run:", run_dirs, format_func=lambda p: p.name)

    match_dir = selected_run / "07_final_scored"
    serp_dir = selected_run / "04_serp_jsonl_input"

    match_files = sorted(match_dir.glob("*.jsonl"))
    serp_files = sorted(serp_dir.glob("*.jsonl"))

    if not match_files or not serp_files:
        st.warning("This run has no valid match/SERP files.")
        return

    selected_match_file = st.selectbox("Select Final Match File:", match_files)
    selected_serp_file = st.selectbox("Select SERP Info File:", serp_files)

    # === Step 2: Load and display ===
    match_data = load_jsonl(selected_match_file)
    serp_data = load_jsonl(selected_serp_file)

    # === Compact Summary Table ===
    st.subheader("📋 Compact Match Table")

    table_data = []
    for entry in match_data:
        s = entry["summary"]
        table_data.append({
            "Line": entry["line_number"],
            "Job Title": s.get("job_title"),
            "Company": s.get("company_name"),
            "Country": s.get("country"),
            "Visa Required": s.get("visa_sponsorship_required"),
            "Culture": s.get("company_culture"),
            "Match?": s.get("potential_match"),
            "Apply?": s.get("recommend_apply"),
            "SERP URL": entry.get("serp_url"),
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)

    # === Original Expander Cards (optional, can be removed) ===
    with st.expander("🔍 View Detailed Match Cards", expanded=False):
        for entry in match_data:
            s = entry["summary"]
            match_flag = "✅ Yes" if s["potential_match"] == "Yes" else "❌ No"
            apply_flag = "✅ Yes" if s["recommend_apply"] == "Yes" else "❌ No"

            with st.expander(f"{s['job_title']} at {s['company_name']} — Apply: {apply_flag} | Match: {match_flag}"):
                st.markdown(f"**Country:** {s.get('country', 'Unknown')}")
                st.markdown(f"**Visa Sponsorship Required:** {s.get('visa_sponsorship_required', 'Unknown')}")
                st.markdown(f"**Company Culture:** {s.get('company_culture', 'Unknown')}")
                st.markdown(f"**SERP URL:** [Link]({entry['serp_url']})")

                st.markdown("**Significant Experience Gaps:**")
                for gap in s.get("significant_experience_gaps", []):
                    st.markdown(f"- {gap}")

                st.markdown("**Recommendation Reasons:**")
                for reason in s.get("recommendation_reasons", []):
                    st.markdown(f"- {reason}")


    st.subheader("🌐 URL Preview Table")

    url_table = [
        {
            "Line": e["line_number"],
            "Job Title": e["summary"]["job_title"],
            "Company": e["summary"]["company_name"],
            "SERP URL": e["serp_url"]
        }
        for e in match_data
    ]

    st.dataframe(pd.DataFrame(url_table), use_container_width=True)
