"""Configuration météo Morez."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Coordonnées Morez (Jura, 39)
LAT = 46.5271
LON = 6.0162
LOCATION = "Morez, Jura (39)"
TIMEZONE = "Europe/Paris"

# Données depuis le
HISTORY_START = "2026-01-01"

# Dossiers
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
CSV_FILE = DATA_DIR / "precipitation.csv"

# GitHub
GITHUB_REPO = "jura39bot/morez-meteo"
GIT_USER = "jura39bot"
GIT_EMAIL = "jura39bot@gmail.com"
