# app/main.py
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


# Add the root directory (parent of `app/`) to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

# Lazy import view modules
from views import query_tab, control_tab, results_tab, jinja_editor_tab, config_tab, json_editor_tab

TAB_MAP = {
    "🔍 Query Jobs": query_tab,
    "🛠️ Flow Panel": control_tab,
    "📊 Results": results_tab,
    "📝 Prompt Editor": jinja_editor_tab,  # 👈 New tab
    "✏️ Schema Editor": json_editor_tab,
    "⚙️ Config": config_tab,
}


st.set_page_config(page_title="Job SERP Pipeline", layout="wide")  # ✅ First Streamlit call


def main():
    st.title("🚀 Job SERP Explorer")

    selected_tab = st.sidebar.radio("Navigation", list(TAB_MAP.keys()))

    # Ensure session state holds a run_uid
    st.session_state.setdefault("last_run_uid", None)

    # Render tab
    TAB_MAP[selected_tab].render()

if __name__ == "__main__":
    main()
