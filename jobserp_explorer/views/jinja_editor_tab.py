import streamlit as st
from pathlib import Path

# Path to your Jinja2 template
from jobserp_explorer.config.paths import JINJA_FILE_PATH

def render():
    st.header("📝 Jinja2 Prompt Editor")
    st.caption("Edit the template used for tailoring to the candidate. Changes are saved to the local file system.")

    # Load file contents
    if JINJA_FILE_PATH.exists():
        content = JINJA_FILE_PATH.read_text()
    else:
        content = ""

    # Code editor (multiline text area or Streamlit's beta_code_editor if using st-extras)
    edited = st.text_area("Edit Template", value=content, height=500, label_visibility="collapsed")

    # Save button
    if st.button("💾 Save Changes to File"):
        try:
            JINJA_FILE_PATH.write_text(edited)
            st.success(f"Template saved to {JINJA_FILE_PATH}")
        except Exception as e:
            st.error(f"Error saving file: {e}")
