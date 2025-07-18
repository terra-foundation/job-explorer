# app/main.py
import sys
import os
from pathlib import Path

import streamlit as st

# Add the root directory (parent of `app/`) to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# import os
# import sys
# import streamlit as st

# st.subheader("Environment Sanity Check")

# st.write("🧪 Python executable:")
# st.code(sys.executable)

# st.write("🧪 sys.path (first 5 entries):")
# st.code("\n".join(sys.path[:5]))

# try:
#     import promptflow
#     st.success(f"promptflow loaded from: {promptflow.__file__}")
# except ImportError as e:
#     st.error(f"promptflow not importable: {e}")



# try:
#     from promptflow.core import tool
#     st.success("Successfully imported: promptflow.core.tool")
# except Exception as e:
#     st.error(f"Import failed: {e}")



import os
import json

from dotenv import load_dotenv
load_dotenv()



from promptflow.client import PFClient
from promptflow.entities import OpenAIConnection

# def ensure_openai_connection(name="open_ai_connection"):
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

#     pf = PFClient()
#     existing = [c.name for c in pf.connections.list()]
#     if name not in existing:
#         conn = OpenAIConnection(
#             name=name,
#             api_key=api_key,
#             api_base="https://api.openai.com/v1",
#             api_version="2024-06-01-preview",
#         )
#         pf.connections.create_or_update(conn)
#         print(f"[✓] Created promptflow connection `{name}`")
#     else:
#         print(f"[✓] Found existing connection `{name}`")


import os
from promptflow.entities import OpenAIConnection

def get_runtime_openai_connection():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAIConnection.from_env()


# ensure_promptflow_connection()

# /home/matias/repos/jobserp_explorer/.env
# os.environ["OPENAI_API_KEY"]

def ensure_dependencies(modules):
    missing = []
    for m in modules:
        try:
            __import__(m)
        except ImportError:
            missing.append(m)
    if missing:
        st.error(f"Missing Python modules: {', '.join(missing)} — try reloading after install completes.")
        st.stop()

ensure_dependencies(["requests", "pandas", "openai"])


# Lazy import view modules
from views import query_tab, control_tab, results_tab, jinja_editor_tab, config_tab, json_editor_tab

TAB_MAP = {
    "🔍 Query Jobs": query_tab,
    "🛠️ Flow Panel": control_tab,
    "📊 Results": results_tab,
    "📝 Prompt Editor": jinja_editor_tab,
    "✏️ Schema Editor": json_editor_tab,
    "⚙️ Config": config_tab,
    # "Debug": debugger,
}

# ✅ First Streamlit call
st.set_page_config(page_title="Job SERP Explorer", layout="wide")

# --- KEY HANDLING: BYOK support with fallback ---
st.sidebar.markdown("### 🔐 OpenAI Key Setup")

# Prompt user for OpenAI API key (masked)
user_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")

if user_key:
    os.environ["OPENAI_API_KEY"] = user_key
    st.sidebar.success("API Key set successfully.")
else:
    # Fallback to loading local .env only if no manual key provided
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        st.sidebar.warning("No API key found. App may not run correctly without it.")
        # You can also trigger a 'demo mode' here if desired

# --- KEY HANDLING: BYOK support with fallback ---
st.sidebar.markdown("### 🔐 Spider Key Setup")

# Prompt user for Spider API key (masked)
spider_key = st.sidebar.text_input("Enter your Spider API Key", type="password")

if spider_key:
    os.environ["SPIDER_API_KEY"] = spider_key
    st.sidebar.success("API Key set successfully.")
else:
    # Fallback to loading local .env only if no manual key provided
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("SPIDER_API_KEY"):
        st.sidebar.warning("No API key found. App may not run correctly without it.")
        # You can also trigger a 'demo mode' here if desired


import os
os.environ["PYTHON_KEYRING_BACKEND"] = "keyrings.alt.file.PlaintextKeyring"


# --- Main App ---
def main():
    st.title("🚀 Job SERP Explorer")



    # Ask for API key
    # user_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
    if user_key:
        os.environ["OPENAI_API_KEY"] = user_key
        # st.sidebar.success("API Key set successfully.")
    else:
        from dotenv import load_dotenv
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            st.sidebar.warning("No API key found. App may not run correctly without it.")
            return  # ⬅ prevent app from continuing

    # ✅ Now it's safe to ensure PF connection
    try:
        get_runtime_openai_connection()
    except Exception as e:
        st.error(f"Failed to set up PromptFlow connection: {e}")
        return


    # # ✅ Now it's safe to ensure PF connection
    # try:
    #     ensure_connection()
    # except Exception as e:
    #     st.error(f"Failed to set up connection: {e}")
    #     return



    selected_tab = st.sidebar.radio("Navigation", list(TAB_MAP.keys()))

    # Ensure session state holds a run_uid
    st.session_state.setdefault("last_run_uid", None)

    # Render tab
    TAB_MAP[selected_tab].render()

    

if __name__ == "__main__":
    main()
