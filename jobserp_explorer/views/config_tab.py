
# app/views/config_tab.py
import streamlit as st
from pathlib import Path
import json

# import sys
# sys.path.append('./../')

from jobserp_explorer.config.schema import AppConfig

CONFIG_PATH = Path("app_config.json")

def render():
    st.title("⚙️ Configuration Settings")

    config = AppConfig.from_json(CONFIG_PATH)

    # 🗂️ Directories
    st.header("📁 Paths")
    config.base_data_dir = st.text_input("Base Data Directory", config.base_data_dir)
    config.run_format = st.text_input("Run Folder Format", config.run_format)

    # 🔍 Query
    st.header("🔍 Default Query Settings")
    config.default_query = st.text_input("Default Job Title", config.default_query)
    config.default_location = st.text_input("Default Location", config.default_location)
    config.result_limit = st.slider("Default Result Limit", 1, 50, config.result_limit)

    # 🤖 PromptFlow
    st.header("🤖 PromptFlow Config")
    config.promptflow.job_match = st.text_input("Job Match Flow Dir", config.promptflow.job_match)
    config.promptflow.page_classifier = st.text_input("Page Classifier Flow Dir", config.promptflow.page_classifier)

    # 🧪 Debugging
    st.header("🧪 Developer Options")
    config.debug = st.checkbox("Enable Debug Logs", config.debug)

    # 💾 Save
    if st.button("💾 Save Configuration"):
        CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2))
        st.success("✅ Configuration saved to `app_config.json`.")
