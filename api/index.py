import sys
from pathlib import Path

# Add project root and execution directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "execution"))

from execution.web_server import app

# Vercel Serverless Function entry point
handler = app
