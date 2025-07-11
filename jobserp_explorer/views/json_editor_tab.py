# app/views/editor_tab.py

import streamlit as st
import json
from pathlib import Path

# Paths

from jobserp_explorer.config.paths import SCHEMA_PATH, DEFAULT_SCHEMA_PATH

def load_schema(path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        st.error(f"Error loading JSON: {e}")
        return {}

def save_schema(schema, path):
    try:
        path.write_text(json.dumps(schema, indent=2))
        st.success("Schema saved successfully.")
    except Exception as e:
        st.error(f"Failed to save schema: {e}")

def render():
    st.header("🛠️ JSON Schema Editor")

    current_schema = load_schema(SCHEMA_PATH)
    schema_text = st.text_area("Edit Schema (JSON format)", value=json.dumps(current_schema, indent=2), height=600)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save"):
            try:
                parsed = json.loads(schema_text)
                save_schema(parsed, SCHEMA_PATH)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")

    with col2:
        if st.button("🔄 Restore Default"):
            default_schema = load_schema(DEFAULT_SCHEMA_PATH)
            save_schema(default_schema, SCHEMA_PATH)
            st.rerun()
