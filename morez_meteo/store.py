"""Lecture/écriture du CSV de précipitations."""
import csv
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

HEADERS = ["date", "precipitation_mm"]


def load_csv(path: Path) -> dict[str, float]:
    """Charge le CSV existant. Retourne un dict {date_str: mm}."""
    if not path.exists():
        return {}
    data = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            data[row["date"]] = float(row["precipitation_mm"])
    return data


def save_csv(path: Path, data: dict[str, float]) -> None:
    """Sauvegarde toutes les données triées par date."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_dates = sorted(data.keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for d in sorted_dates:
            writer.writerow({"date": d, "precipitation_mm": data[d]})
    log.info(f"CSV sauvegardé : {len(sorted_dates)} lignes → {path}")


def merge(existing: dict[str, float], new: dict[str, float]) -> tuple[dict[str, float], int]:
    """
    Fusionne nouvelles données dans l'existant.
    Retourne (merged, nb_nouveaux_jours).
    """
    merged = dict(existing)
    added = 0
    for d, mm in new.items():
        if d not in merged:
            added += 1
        merged[d] = mm  # Toujours mettre à jour (correction possible)
    return merged, added
