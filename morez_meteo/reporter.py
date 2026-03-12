"""Génère les rapports hebdomadaires, mensuels, annuels."""
import json
import logging
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}


def _week_key(d: date) -> str:
    """Retourne 'YYYY-Www' (ex: '2026-W10')."""
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_range(d: date) -> tuple[date, date]:
    """Lundi → dimanche de la semaine contenant d."""
    monday = d - timedelta(days=d.weekday())
    return monday, monday + timedelta(days=6)


def build_stats(data: dict[str, float]) -> dict:
    """Calcule les stats par jour/semaine/mois/année."""
    by_week = defaultdict(float)
    by_month = defaultdict(float)
    by_year = defaultdict(float)
    days_in_month = defaultdict(int)
    days_in_week = defaultdict(int)
    wet_days_month = defaultdict(int)

    for date_str, mm in data.items():
        d = date.fromisoformat(date_str)
        wk = _week_key(d)
        mo = f"{d.year}-{d.month:02d}"
        yr = str(d.year)

        by_week[wk] += mm
        by_month[mo] += mm
        by_year[yr] += mm
        days_in_month[mo] += 1
        days_in_week[wk] += 1
        if mm > 0.1:
            wet_days_month[mo] += 1

    return {
        "by_week": {k: round(v, 1) for k, v in sorted(by_week.items())},
        "by_month": {k: round(v, 1) for k, v in sorted(by_month.items())},
        "by_year": {k: round(v, 1) for k, v in sorted(by_year.items())},
        "days_in_month": dict(days_in_month),
        "days_in_week": dict(days_in_week),
        "wet_days_month": dict(wet_days_month),
    }


def save_json(reports_dir: Path, stats: dict) -> None:
    """Sauvegarde les stats complètes en JSON."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "stats.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    log.info(f"JSON sauvegardé : {path}")


def _ranking_table(ranking: dict, year: str, today_str: str, full_year: bool = False) -> list[str]:
    """Génère le bloc Markdown d'un classement pour une année donnée."""
    period = f"01/01/{year} → 31/12/{year}" if full_year else f"01/01/{year} → {today_str}"
    lines = [
        f"## 🏆 Top 10 villes les plus pluvieuses — France métropolitaine ({year})",
        f"",
        f"> Période : {period} · {ranking['total_cities']} villes comparées",
        f"",
        "| # | Ville | Total (mm) |",
        "|---|-------|-----------|",
    ]
    for i, (city, total) in enumerate(ranking["top"], 1):
        is_morez = city == "Morez"
        marker = " ⬅️" if is_morez else ""
        b = "**" if is_morez else ""
        lines.append(f"| {i} | {b}{city}{marker}{b} | {b}{total:.1f}{b} |")

    morez_rank = ranking["morez_rank"]
    total_cities = ranking["total_cities"]
    if morez_rank > 10:
        lines += [
            f"",
            f"> 📍 Morez est **{morez_rank}e** sur {total_cities} villes "
            f"({ranking['morez_total']:.1f} mm)",
        ]
    lines.append("")
    return lines


def generate_markdown(
    data: dict[str, float],
    stats: dict,
    location: str,
    ranking_current: dict | None = None,
    ranking_prev: dict | None = None,
    prev_year: str | None = None,
) -> str:
    """Génère le rapport Markdown complet."""
    today = date.today()
    lines = [
        f"# 🌧️ Précipitations — {location}",
        f"",
        f"> Données Open-Meteo · Mise à jour : {today.isoformat()}",
        f"",
    ]

    # ── Bilan annuel ──────────────────────────────────────────────────────────
    lines += ["## 📅 Bilan annuel", ""]
    lines += ["| Année | Total (mm) |", "|-------|-----------|"]
    for yr, total in stats["by_year"].items():
        lines.append(f"| {yr} | **{total:.1f}** |")
    lines.append("")

    # ── Top 10 — Année courante ────────────────────────────────────────────────
    yr_label = today.strftime("%Y")
    today_str = today.strftime("%d/%m/%Y")
    if ranking_current:
        lines += _ranking_table(ranking_current, yr_label, today_str, full_year=False)

    # ── Top 10 — Année précédente (bilan complet) ─────────────────────────────
    if ranking_prev and prev_year:
        lines += _ranking_table(ranking_prev, prev_year, "", full_year=True)

    # ── Bilan mensuel ─────────────────────────────────────────────────────────
    lines += ["## 📆 Bilan mensuel", ""]
    lines += ["| Mois | Total (mm) | Jours de pluie | Jours mesurés |", "|------|-----------|----------------|--------------|"]
    for mo, total in stats["by_month"].items():
        yr, m = mo.split("-")
        label = f"{MOIS_FR[int(m)]} {yr}"
        nb_days = stats["days_in_month"].get(mo, 0)
        wet = stats["wet_days_month"].get(mo, 0)
        lines.append(f"| {label} | {total:.1f} | {wet} | {nb_days} |")
    lines.append("")

    # ── Bilan hebdomadaire (12 dernières semaines) ────────────────────────────
    lines += ["## 📊 Bilan hebdomadaire (12 dernières semaines)", ""]
    lines += ["| Semaine | Période | Total (mm) |", "|---------|---------|-----------|"]
    weeks = sorted(stats["by_week"].items())[-12:]
    for wk, total in weeks:
        yr, w = wk.split("-W")
        # Calculer le lundi de cette semaine
        monday = date.fromisocalendar(int(yr), int(w), 1)
        sunday = monday + timedelta(days=6)
        period = f"{monday.strftime('%d/%m')} → {sunday.strftime('%d/%m/%Y')}"
        lines.append(f"| {wk} | {period} | {total:.1f} |")
    lines.append("")

    # ── Derniers 30 jours ────────────────────────────────────────────────────
    lines += ["## 🗓️ Détail — 30 derniers jours", ""]
    lines += ["| Date | Précipitations (mm) |", "|------|---------------------|"]
    recent = sorted(data.items())[-30:]
    for d, mm in recent:
        icon = "🌧️" if mm > 5 else ("🌦️" if mm > 0.1 else "☀️")
        lines.append(f"| {d} | {icon} {mm:.1f} |")
    lines.append("")

    # ── Totaux résumé ─────────────────────────────────────────────────────────
    total_all = sum(data.values())
    current_month = today.strftime("%Y-%m")
    total_month = stats["by_month"].get(current_month, 0)
    current_week = _week_key(today)
    total_week = stats["by_week"].get(current_week, 0)

    lines += [
        "## 📌 Résumé",
        "",
        f"- **Cette semaine** : {total_week:.1f} mm",
        f"- **Ce mois** : {total_month:.1f} mm",
        f"- **Total depuis le 01/01/2026** : {total_all:.1f} mm",
        f"- **Nombre de jours mesurés** : {len(data)}",
        "",
        "---",
        f"*Source : [Open-Meteo](https://open-meteo.com/) · "
        f"[Archive API](https://archive-api.open-meteo.com/)*",
    ]

    return "\n".join(lines)


def save_markdown(reports_dir: Path, content: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "README.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    log.info(f"Markdown sauvegardé : {path}")
