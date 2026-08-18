#!/usr/bin/env python3
"""
run_web.py — Easy Local Runner for GMB Leads Enrichment Web App.

Usage:
    python run_web.py
    # or
    python run_web.py --port 8080
"""

import argparse
import sys
import webbrowser
from pathlib import Path

# Add project root and execution directory to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "execution"))

def main():
    parser = argparse.ArgumentParser(description="Run GMB Leads Enrichment Local Web App")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        import subprocess
        print("Installing uvicorn...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi", "-q"])
        import uvicorn

    url = f"http://{args.host}:{args.port}"
    print(f"\n=======================================================")
    print(f" 🚀 GMB Leads Engine & Enrichment Web App Running!")
    print(f" 🌐 Access Local Web UI: \033[1;32m{url}\033[0m")
    print(f"=======================================================\n")

    if not args.no_browser:
        # Schedule browser opening
        import threading
        import time
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("web_server:app", host=args.host, port=args.port, reload=True, app_dir=str(PROJECT_ROOT / "execution"))

if __name__ == "__main__":
    main()
