"""Wrapper to start uvicorn from the correct working directory."""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import uvicorn  # noqa: E402
uvicorn.run("main:app", host="0.0.0.0", port=8000)
