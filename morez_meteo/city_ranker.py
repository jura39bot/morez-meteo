"""
Classement pluviométrique des villes françaises vs Morez.
Données Open-Meteo — mise en cache hebdomadaire pour ne pas surcharger l'API.
"""

import json
import logging
import time
import urllib.request
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from .french_cities import FRENCH_CITIES

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE_TTL_DAYS = 7  # Rafraîchi une fois par semaine


def _fetch_city_total(name: str, lat: float, lon: float, start: str, end: str) -> float:
    """Récupère le total de précipitations d'une ville sur la période."""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum",
        "timezone": "Europe/Paris",
    })
    url = f"{ARCHIVE_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "morez-meteo/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            values = data["daily"]["precipitation_sum"]
            return round(sum(v or 0 for v in values), 1)
    except Exception as e:
        log.warning(f"Erreur fetch {name}: {e}")
        return 0.0


def fetch_all_cities(start: str, end: str, cache_dir: Path) -> dict[str, float]:
    """
    Récupère les précipitations de toutes les villes de référence.
    Cache par année (stable key) pour l'année courante, permanent pour les années passées.
    TTL 7 jours pour l'année courante.
    """
    today = date.today()
    end_d = date.fromisoformat(end)
    is_past_year = end_d.year < today.year  # Année révolue → cache permanent

    # Clé stable par année (pas par end_date) pour éviter un re-fetch quotidien
    year_key = start[:4]
    cache_path = cache_dir / f"cities_cache_{year_key}.json"

    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            cached_date = date.fromisoformat(cached.get("fetched_date", "2000-01-01"))
            if is_past_year or (today - cached_date).days < CACHE_TTL_DAYS:
                log.info(f"Cache villes valide ({cached_date}, {year_key}) — {len(cached['data'])} villes")
                return cached["data"]
        except Exception:
            pass

    log.info(f"Fetch précipitations {len(FRENCH_CITIES)} villes ({start} → {end})...")
    results = {}
    for name, lat, lon in FRENCH_CITIES:
        total = _fetch_city_total(name, lat, lon, start, end)
        results[name] = total
        log.debug(f"  {name}: {total} mm")
        time.sleep(0.3)

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({
        "fetched_date": today.isoformat(),
        "start_date": start,
        "end_date": end,
        "data": results,
    }, indent=2))
    log.info(f"Cache villes sauvegardé : {cache_path}")
    return results


def build_ranking(
    morez_total: float,
    cities_data: dict[str, float],
    top_n: int = 10,
) -> dict:
    """
    Construit le classement : Morez + villes de référence, trié par précipitations desc.
    Retourne le top N + la position de Morez.
    """
    all_entries = dict(cities_data)
    all_entries["Morez"] = morez_total

    ranked = sorted(all_entries.items(), key=lambda x: x[1], reverse=True)
    morez_rank = next(i + 1 for i, (name, _) in enumerate(ranked) if name == "Morez")

    return {
        "top": ranked[:top_n],
        "morez_rank": morez_rank,
        "total_cities": len(ranked),
        "morez_total": morez_total,
    }
