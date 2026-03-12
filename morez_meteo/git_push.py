"""Commit et push automatique vers GitHub."""
import logging
import subprocess
from pathlib import Path
from datetime import date

log = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def setup_git(repo_dir: Path, user: str, email: str, remote_url: str) -> None:
    """Configure git si pas déjà fait."""
    _run(["git", "config", "user.name", user], repo_dir)
    _run(["git", "config", "user.email", email], repo_dir)
    # Vérifier/ajouter le remote
    code, out = _run(["git", "remote", "get-url", "origin"], repo_dir)
    if code != 0:
        _run(["git", "remote", "add", "origin", remote_url], repo_dir)
        log.info(f"Remote origin ajouté : {remote_url}")


def commit_and_push(repo_dir: Path, added: int) -> bool:
    """
    Stage tous les fichiers modifiés, commit et push.
    Retourne True si commit effectué.
    """
    today = date.today().isoformat()

    # Stage
    code, out = _run(["git", "add", "-A"], repo_dir)
    if code != 0:
        log.error(f"git add échoué : {out}")
        return False

    # Vérifier si y a quelque chose à committer
    code, out = _run(["git", "status", "--porcelain"], repo_dir)
    if not out.strip():
        log.info("Rien à committer (données déjà à jour)")
        return False

    # Commit
    msg = f"data: précipitations {today} (+{added} jours)" if added > 0 else f"data: précipitations {today}"
    code, out = _run(["git", "commit", "-m", msg], repo_dir)
    if code != 0:
        log.error(f"git commit échoué : {out}")
        return False
    log.info(f"Commit : {msg}")

    # Push
    code, out = _run(["git", "push", "origin", "main"], repo_dir)
    if code != 0:
        # Essayer master si main échoue
        code, out = _run(["git", "push", "origin", "master"], repo_dir)
    if code != 0:
        log.error(f"git push échoué : {out}")
        return False

    log.info(f"Push GitHub OK")
    return True
