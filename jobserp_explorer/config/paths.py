from pathlib import Path

# Assume this file lives in: app/config/paths.py
BASE_DIR = Path(__file__).resolve().parents[2]  # goes up from /app/config/paths.py → /app → root

DATA_DIR = BASE_DIR / "data" / "01_fetch_serps"
FLOWS_DIR = BASE_DIR / "jobserp_explorer"

FLOW_JOBPOSTING_DIR = FLOWS_DIR / "flow_jobposting"

# File paths
JINJA_FILE_PATH = FLOW_JOBPOSTING_DIR / "session_summarizer3.jinja2"
SCHEMA_PATH = FLOW_JOBPOSTING_DIR / "session_schema3.json"
DEFAULT_SCHEMA_PATH = FLOW_JOBPOSTING_DIR / "default_schema.json"


# Path for saved queries
QUERY_OUTPUT_DIR = DATA_DIR / "query_data"

# Metadata file
METADATA_FILE = DATA_DIR / "metadata.json"

# Default run config
DEFAULT_LIMIT = 20
