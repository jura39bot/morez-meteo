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
CACHE_TTL_DAYS = 1  # 1 jour : le classement doit être calculé sur la MÊME fenêtre que Morez
# L'archive est à jour (vérifié le 05/11/2026 : Montpellier 39,5 + 91,1 mm
# les 04 et 05/11). Un 0.0 signifie "pas de pluie", pas "pas de donnée".
RANKING_LAG_DAYS = 0
HISTORY_CACHE = "history_yearly.json"


def ranking_end(today: date | None = None) -> str:
    """Dernier jour de la fenêtre de classement (archive à jour -> aujourd'hui)."""
    d = today or date.today()
    return (d - timedelta(days=RANKING_LAG_DAYS)).isoformat()


def _fetch_series(lat: float, lon: float, start: str, end: str):
    """Série journalière (dates, valeurs) sur une fenêtre."""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum",
        "timezone": "Europe/Paris",
    })
    url = f"{ARCHIVE_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "morez-meteo/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["daily"]["time"], data["daily"]["precipitation_sum"]


def _fetch_city_total(name: str, lat: float, lon: float, start: str, end: str) -> float:
    """Récupère le total de précipitations d'une ville sur la période."""
    try:
        _, values = _fetch_series(lat, lon, start, end)
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
            # IMPORTANT : on ne réutilise le cache que s'il porte sur la MÊME fenêtre
            # (sinon les villes s'arrêtent plus tôt que Morez → faux classement)
            same_window = cached.get("end_date") == end
            if is_past_year or (same_window and (today - cached_date).days < CACHE_TTL_DAYS):
                log.info(f"Cache villes valide ({cached_date}, {year_key}, -> {cached.get('end_date')}) — {len(cached['data'])} villes")
                return cached["data"]
            log.info(f"Cache villes périmé (fin {cached.get('end_date')} != {end}) → recalcul")
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
    payload = {
        "fetched_date": today.isoformat(),
        "start_date": start,
        "end_date": end,
        "source": "open-meteo archive (ERA5/IFS) — même fenêtre et même source pour toutes les villes, Morez inclus",
        "data": results,
    }
    cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    # fichier historique (nom générique) : on le garde à jour pour ne pas laisser de données périmées
    if start[:4] == str(today.year):
        (cache_dir / "cities_precipitation_cache.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info(f"Cache villes sauvegardé : {cache_path}")
    return results


def fetch_place_total(lat: float, lon: float, start: str, end: str) -> float:
    """Total de précipitations d'un lieu (ex. Morez) sur la MÊME fenêtre et la MÊME source
    que les villes de référence → comparaison honnête."""
    return _fetch_city_total("Morez", lat, lon, start, end)


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


def fetch_history(lat: float, lon: float, cache_dir: Path, first_year: int = 2019) -> dict:
    """Totaux annuels des annees revolues + cumul nov+dec (cache permanent)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / HISTORY_CACHE
    last_full = date.today().year - 1
    if path.exists():
        try:
            c = json.loads(path.read_text())
            if c.get("last_full_year") == last_full and c.get("first_year") == first_year:
                return c
        except Exception:
            pass

    years, novdec = {}, {}
    for y in range(first_year, last_full + 1):
        log.info(f"Historique {y}...")
        try:
            t, v = _fetch_series(lat, lon, f"{y}-01-01", f"{y}-12-31")
        except Exception as e:
            log.warning(f"Erreur historique {y}: {e}")
            continue
        years[str(y)] = round(sum(x or 0 for x in v), 1)
        novdec[str(y)] = round(sum((x or 0) for d, x in zip(t, v) if d[5:7] in ("11", "12")), 1)
        time.sleep(0.3)

    payload = {
        "first_year": first_year,
        "last_full_year": last_full,
        "years": years,
        "nov_dec": novdec,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def project_year(ytd: float, history: dict) -> dict:
    """Projection de fin d'annee = cumul + moyenne nov/dec des annees passees."""
    nd = [v for v in history.get("nov_dec", {}).values() if v]
    vals = [v for v in history.get("years", {}).values() if v]
    avg_nd = sum(nd) / len(nd) if nd else 0.0
    avg_year = sum(vals) / len(vals) if vals else 0.0
    proj = ytd + avg_nd
    delta = round((proj - avg_year) / avg_year * 100, 1) if avg_year else 0.0
    return {
        "projection": round(proj, 1),
        "avg_year": round(avg_year, 1),
        "avg_nov_dec": round(avg_nd, 1),
        "delta_pct": delta,
        "years": history.get("years", {}),
    }
