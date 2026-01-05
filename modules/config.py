from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  

NETBOX_URL = 'http://127.0.0.1:8080/'
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")

DATA_DIR = Path("data")
CSV_DIR = DATA_DIR / "csv"
LOG_DIR = Path("logs")


if not NETBOX_TOKEN:
    raise ValueError("NETBOX_TOKEN not found in .env")

DATA_DIR.mkdir(exist_ok=True)
CSV_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)