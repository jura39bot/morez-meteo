"""Point d'entrée principal — morez-meteo."""
import logging
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def run():
    from . import config
    from .fetcher import fetch_precipitation
    from .store import load_csv, save_csv, merge
    from .reporter import build_stats, save_json, generate_markdown, save_markdown
    from .city_ranker import fetch_all_cities, build_ranking
    from .git_push import commit_and_push

    today = date.today().isoformat()
    log.info(f"=== morez-meteo {today} ===")

    # 1. Charger les données existantes
    existing = load_csv(config.CSV_FILE)
    log.info(f"Données existantes : {len(existing)} jours")

    # 2. Récupérer depuis la dernière date connue (ou depuis HISTORY_START)
    if existing:
        # Reprendre depuis le dernier jour connu (pour éventuelle correction)
        last_date = sorted(existing.keys())[-1]
        fetch_start = last_date  # Re-fetch le dernier jour au cas où
    else:
        fetch_start = config.HISTORY_START

    new_data = fetch_precipitation(fetch_start, today, config.LAT, config.LON, config.TIMEZONE)

    # 3. Fusionner
    merged, added = merge(existing, new_data)
    log.info(f"{added} nouveaux jours ajoutés")

    # 4. Sauvegarder CSV
    save_csv(config.CSV_FILE, merged)

    # 5. Générer les stats
    stats = build_stats(merged)

    # 6. Classement villes françaises (cache 7 jours)
    year_start = f"{date.today().year}-01-01"
    year_end = today
    log.info("Classement pluviométrique villes françaises...")
    cities_data = fetch_all_cities(year_start, year_end, config.DATA_DIR)
    morez_total = stats["by_year"].get(str(date.today().year), 0)
    ranking = build_ranking(morez_total, cities_data, top_n=10)
    log.info(f"Morez : {ranking['morez_rank']}e/{ranking['total_cities']} villes françaises")

    # 7. Générer rapports
    save_json(config.REPORTS_DIR, stats)
    md = generate_markdown(merged, stats, config.LOCATION, ranking=ranking)
    save_markdown(config.REPORTS_DIR, md)

    # 6. Commit + push GitHub
    from .git_push import setup_git
    remote_url = f"https://github.com/{config.GITHUB_REPO}.git"
    setup_git(config.BASE_DIR, config.GIT_USER, config.GIT_EMAIL, remote_url)
    pushed = commit_and_push(config.BASE_DIR, added)

    if pushed:
        log.info(f"✅ Push GitHub OK → https://github.com/{config.GITHUB_REPO}")
    else:
        log.info("Pas de nouveau push (données déjà à jour)")

    log.info("=== Terminé ===")


if __name__ == "__main__":
    run()
