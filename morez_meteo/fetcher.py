"""Récupère les précipitations quotidiennes via Open-Meteo."""
import urllib.request
import urllib.parse
import json
import logging
from datetime import date, timedelta


log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_precipitation(start: str, end: str, lat: float, lon: float, tz: str) -> dict[str, float]:
    """
    Récupère les précipitations journalières (mm) entre start et end.
    Utilise l'API archive pour les données passées, forecast pour aujourd'hui/demain.
    Retourne un dict { 'YYYY-MM-DD': mm }.
    """
    today = date.today()
    results = {}

    # Données historiques (archive)
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    archive_end = min(end_d, today - timedelta(days=1))

    if start_d <= archive_end:
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "start_date": start_d.isoformat(),
            "end_date": archive_end.isoformat(),
            "daily": "precipitation_sum",
            "timezone": tz,
        })
        url = f"{ARCHIVE_URL}?{params}"
        log.info(f"Archive Open-Meteo : {start_d} → {archive_end}")
        data = _get(url)
        for d, mm in zip(data["daily"]["time"], data["daily"]["precipitation_sum"]):
            results[d] = round(float(mm or 0), 1)

    # Données du jour (forecast)
    if end_d >= today:
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum",
            "timezone": tz,
            "forecast_days": 1,
        })
        url = f"{FORECAST_URL}?{params}"
        log.info(f"Forecast Open-Meteo : aujourd'hui {today}")
        data = _get(url)
        for d, mm in zip(data["daily"]["time"], data["daily"]["precipitation_sum"]):
            if d not in results:
                results[d] = round(float(mm or 0), 1)

    log.info(f"Précipitations récupérées : {len(results)} jours")
    return results


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "morez-meteo/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
