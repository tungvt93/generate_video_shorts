import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output_shorts"

# Ensure directories exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default clip limits
MIN_CLIP_DURATION = 8  # seconds
MAX_CLIP_DURATION = 10  # seconds

def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY", "")
