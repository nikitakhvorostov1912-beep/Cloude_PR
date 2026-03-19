"""Interview-to-BPMN launcher — double-click to start.

.pyw extension runs without console window on Windows.
"""
import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

# Set working directory to script location
os.chdir(Path(__file__).parent)

PORT = 8501
URL = f"http://localhost:{PORT}"


def is_ollama_running():
    """Check if Ollama is running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ollama.exe"],
            capture_output=True, text=True, timeout=5
        )
        return "ollama.exe" in result.stdout
    except Exception:
        return False


def start_ollama():
    """Start Ollama if not running."""
    if is_ollama_running():
        return

    ollama_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path("ollama"),
    ]
    for ollama_path in ollama_paths:
        try:
            subprocess.Popen(
                [str(ollama_path), "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time.sleep(3)
            return
        except FileNotFoundError:
            continue


def main():
    # Start Ollama
    start_ollama()

    # Launch Streamlit
    process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "src/web/app.py",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            f"--server.port={PORT}",
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Wait for server to start, then open browser
    for _ in range(30):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen(URL, timeout=2)
            webbrowser.open(URL)
            break
        except Exception:
            continue

    # Keep running until Streamlit exits
    process.wait()


if __name__ == "__main__":
    main()
