"""Preview entry point that sets correct sys.path."""
import os
import sys

# Ensure the project root is in sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now run the Streamlit app
from streamlit.web.cli import main

sys.argv = ["streamlit", "run", os.path.join(project_root, "src", "web", "app.py"),
            "--server.port", "8501", "--server.headless", "true"]
main()
