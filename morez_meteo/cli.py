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

    # 2. Récupérer depuis HISTORY_START (backfill si données manquantes)
    if existing:
        first_date = sorted(existing.keys())[0]
        # Backfill si le CSV ne remonte pas jusqu'à HISTORY_START
        if first_date > config.HISTORY_START:
            log.info(f"Backfill détecté : {config.HISTORY_START} → {first_date}")
            fetch_start = config.HISTORY_START
        else:
            last_date = sorted(existing.keys())[-1]
            fetch_start = last_date  # Re-fetch le dernier pour correction éventuelle
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

    # 6. Classement villes françaises — année courante (cache 7j)
    cur_year = date.today().year
    prev_year = cur_year - 1
    log.info(f"Classement pluviométrique {cur_year}...")
    cities_cur = fetch_all_cities(f"{cur_year}-01-01", today, config.DATA_DIR)
    morez_cur = stats["by_year"].get(str(cur_year), 0)
    ranking_cur = build_ranking(morez_cur, cities_cur, top_n=10)
    log.info(f"Morez {cur_year} : {ranking_cur['morez_rank']}e/{ranking_cur['total_cities']} villes")

    # 7. Classement villes françaises — année précédente (cache permanent)
    log.info(f"Classement pluviométrique {prev_year}...")
    cities_prev = fetch_all_cities(f"{prev_year}-01-01", f"{prev_year}-12-31", config.DATA_DIR)
    morez_prev = stats["by_year"].get(str(prev_year), 0)
    ranking_prev = build_ranking(morez_prev, cities_prev, top_n=10)
    log.info(f"Morez {prev_year} : {ranking_prev['morez_rank']}e/{ranking_prev['total_cities']} villes")

    # 8. Générer rapports
    save_json(config.REPORTS_DIR, stats)
    md = generate_markdown(
        merged, stats, config.LOCATION,
        ranking_current=ranking_cur,
        ranking_prev=ranking_prev,
        prev_year=str(prev_year),
    )
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
