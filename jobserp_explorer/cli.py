# jobserp_explorer/cli.py
import subprocess
from pathlib import Path

def main():
    path = Path(__file__).parent / "app.py"
    subprocess.run(["streamlit", "run", str(path)])
