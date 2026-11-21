"""Archive loop: decrypt every released case into past-cases/case_NNN/.

Read-only towards the game: it never submits. It fetches a game's key only once
the game's start_time has passed (never before release), with at most a few
requests per game, so it can run next to the live `watch` bot.

On start it backfills every already-started game that is missing from
past-cases/, then sleeps until the next start_time.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

from . import config
from .api import GameAPI
from .case import extract_zip

PAST_DIR = config.ROOT / "past-cases"
README = PAST_DIR / "README.md"
KEEP_SUFFIXES = {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _parse(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _fetch_key(api: GameAPI, game_id: int) -> str | None:
    """A few spaced tries; 403 means the server does not consider the game started yet."""
    for _ in range(5):
        try:
            return api.get_key(game_id)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            print(f"{_ts()} game {game_id}: key HTTP {code}")
        except requests.RequestException as e:
            print(f"{_ts()} game {game_id}: key request failed: {e!r}")
        time.sleep(3)
    return None


def _first_sentence(text: str, limit: int = 140) -> str:
    s = " ".join(text.split())
    s = s.split(". ")[0].rstrip(".")
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s.replace("|", "\\|")


def _add_readme_row(case_id: int, target: Path) -> None:
    if not README.exists():
        return
    text = README.read_text()
    if f"]({target.name}/)" in text:
        return
    desc = target / "description.txt"
    claim = _first_sentence(desc.read_text(errors="replace")) if desc.exists() else "?"
    row = f"| [{case_id}]({target.name}/) | {claim} | todo | todo | todo | still open |"
    lines = text.splitlines()
    # Insert after the last table row so the notes below the table stay below it.
    last = max((i for i, ln in enumerate(lines) if ln.startswith("| [")), default=len(lines) - 1)
    lines.insert(last + 1, row)
    README.write_text("\n".join(lines) + "\n")


def archive_case(api: GameAPI, game_id: int) -> bool:
    target = PAST_DIR / f"case_{game_id:03d}"
    if target.exists():
        return True
    zip_path = config.CASES_DIR / f"case_{game_id:03d}.zip"
    if not zip_path.exists():
        print(f"{_ts()} game {game_id}: MISSING {zip_path}")
        return False
    key = _fetch_key(api, game_id)
    if key is None:
        print(f"{_ts()} game {game_id}: no key, will retry later")
        return False
    # Decrypt into a fresh, empty dir first; only data files are copied over.
    tmp = extract_zip(zip_path, key, config.WORK_DIR / f"archive_{game_id:03d}")
    target.mkdir(parents=True)
    for f in sorted(tmp.rglob("*")):
        if f.is_file() and not f.is_symlink() and f.suffix.lower() in KEEP_SUFFIXES:
            shutil.copy2(f, target / f.name)
    pdf = target / "invoices.pdf"
    if pdf.exists():
        reader = PdfReader(str(pdf))
        (target / "invoice.txt").write_text("\n\n".join((p.extract_text() or "") for p in reader.pages))
    _add_readme_row(game_id, target)
    print(f"{_ts()} game {game_id}: saved {target} ({', '.join(p.name for p in sorted(target.iterdir()))})")
    return True


# ---- our results, from the organisers' public leaderboard ---------------------------------
# Only OUR team's rows are fetched, and only aggregates without other teams' names or
# individual amounts are written (data-handling rule in research/03-leaderboard-findings.md).

TEAM = os.getenv("CLAIMS_TEAM", "Kiebler Software Solutions")
RESULTS_HEADER = "## Our results per game"
RESULTS_COLS = (
    "| Game | Net | Income | Costs | Our charges `a` per line (accepted/teams, verdict) | Our reviews (wrongly rejected fair / accepted paid) |\n"
    "| --- | ---: | ---: | ---: | --- | --- |"
)


def _lb():
    """research/live/lb_analyze.py is our own script, not a package; load it by path."""
    path = config.ROOT / "research" / "live" / "lb_analyze.py"
    spec = importlib.util.spec_from_file_location("lb_analyze", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _completed_games(lb) -> set[int]:
    d = lb.Source().get("games", completed_only="true", page_size=1000)
    return {g["id"] for g in (d or {}).get("items", []) if g.get("status") == "completed"}


def _short_verdict(v: str) -> str:
    return "fair" if v.startswith("fair") else "inflated" if v.startswith("INFLATED") else "?"


def save_results(lb, game_id: int) -> bool:
    target = PAST_DIR / f"case_{game_id:03d}"
    out = target / "results.json"
    if out.exists() or not target.exists():
        return out.exists()
    rows = lb.tx_pages(lb.Source(), game_id, TEAM)  # no disk cache: a cache from mid-game could be incomplete
    if not rows:
        print(f"{_ts()} game {game_id}: no result rows for {TEAM!r} yet")
        return False
    iv, rv = lb.issuer_view(rows, TEAM), lb.reviewer_view(rows, TEAM)
    for r in rv.values():
        r.pop("charges_seen", None)  # other teams' individual charges stay out of the repo
    income = sum(r["amount"] for r in rows if r["issuer"] == TEAM)
    costs = sum(r["amount"] for r in rows if r["reviewer"] == TEAM)
    res = dict(game=game_id, team=TEAM, net=round(income - costs, 2), income=round(income, 2), costs=round(costs, 2),
               lines={str(k): dict(charge=iv[k], review=rv.get(k)) for k in iv})
    out.write_text(json.dumps(res, indent=2) + "\n")
    _add_results_row(res)
    print(f"{_ts()} game {game_id}: results saved, net {res['net']:+.2f}")
    return True


def _add_results_row(res: dict) -> None:
    if not README.exists():
        return
    text = README.read_text()
    if f"| [{res['game']}](case_{res['game']:03d}/results.json) |" in text:
        return
    charges = "; ".join(
        f"L{k}: 0 (nothing charged)" if v["charge"]["a"] is None else
        f"L{k}: {v['charge']['a']} ({v['charge']['accepted']}/{v['charge']['n']}, {_short_verdict(v['charge']['verdict'])})"
        for k, v in res["lines"].items())
    reviews = "; ".join(
        f"L{k}: {v['review']['wrongly_rejected']} / {v['review']['accepted_paid']}"
        for k, v in res["lines"].items() if v["review"])
    row = (f"| [{res['game']}](case_{res['game']:03d}/results.json) | {res['net']:+.2f} | {res['income']:.2f} | "
           f"{res['costs']:.2f} | {charges} | {reviews} |")
    if RESULTS_HEADER not in text:
        text = text.rstrip("\n") + f"\n\n{RESULTS_HEADER}\n\nFilled in automatically by `claimbot archive` from our own rows on the public leaderboard.\n\n{RESULTS_COLS}\n"
    lines = text.rstrip("\n").splitlines()
    start = lines.index(RESULTS_HEADER)
    rows = [i for i in range(start, len(lines)) if lines[i].startswith("| [")]
    pos = (rows[-1] if rows else start + 5) + 1
    lines.insert(pos, row)
    # keep the results table sorted by game
    block = sorted((ln for ln in lines if ln.startswith("| [") and "/results.json)" in ln),
                   key=lambda ln: int(ln.split("[", 1)[1].split("]", 1)[0]))
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| [") and "/results.json)" in ln]
    for i, ln in zip(idx, block):
        lines[i] = ln
    README.write_text("\n".join(lines) + "\n")


# ---- push past-cases/ (and nothing else) to origin/main ------------------------------------
# The commit is built on top of origin/main in a throwaway index, so the local branch, local
# commits and every other working-tree change stay untouched. Files a teammate added under
# past-cases/ are never deleted (--ignore-removal). README.md is merged three-way against what
# we pushed last, so rows a teammate added on origin are kept.

LAST_README = config.RUNS_DIR / "archive_last_readme.md"  # README as we last pushed it (merge base)
README_PATH = "past-cases/README.md"


def _git(*args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.ROOT, env={**os.environ, **(env or {})},
                          capture_output=True, text=True, check=check)


def _merge_readme(remote: str) -> str | None:
    """Merged README text, or None when ours and theirs conflict (then theirs is kept on origin)."""
    ours = README.read_text()
    theirs = _git("show", f"{remote}:{README_PATH}", check=False)
    if theirs.returncode != 0:
        return ours
    base = LAST_README.read_text() if LAST_README.exists() else _git("show", f"HEAD:{README_PATH}", check=False).stdout
    if theirs.stdout == base or theirs.stdout == ours:
        return ours
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in (("ours", ours), ("base", base), ("theirs", theirs.stdout)):
            p = Path(d) / name
            p.write_text(text)
            paths.append(str(p))
        m = _git("merge-file", "-p", *paths, check=False)
    return m.stdout if m.returncode == 0 else None


def push_cases(message: str) -> None:
    for attempt in range(3):
        _git("fetch", "-q", "origin", "main")
        remote = _git("rev-parse", "origin/main").stdout.strip()
        merged = _merge_readme(remote)
        if merged is None:
            print(f"{_ts()} git: README.md conflicts with origin; pushing case folders only, README stays as on origin")
        elif merged != README.read_text():
            README.write_text(merged)  # pick up a teammate's rows locally too
        with tempfile.NamedTemporaryFile(dir=config.RUNS_DIR, prefix="archive_index_") as idx:
            env = {"GIT_INDEX_FILE": idx.name}
            _git("read-tree", remote, env=env)
            _git("add", "--ignore-removal", "--", "past-cases", env=env)
            if merged is None:
                _git("reset", "-q", remote, "--", README_PATH, env=env)
            tree = _git("write-tree", env=env).stdout.strip()
        if tree == _git("rev-parse", f"{remote}^{{tree}}").stdout.strip():
            return
        commit = _git("commit-tree", tree, "-p", remote, "-m", message).stdout.strip()
        push = _git("push", "-q", "origin", f"{commit}:refs/heads/main", check=False)
        if push.returncode == 0:
            if merged is not None:
                LAST_README.write_text(merged)
            # Stage the same files locally, so a later `git pull` does not stop on
            # "untracked working tree files would be overwritten".
            _git("add", "--ignore-removal", "--", "past-cases", check=False)
            print(f"{_ts()} git: pushed {commit[:7]} to origin/main ({message})")
            return
        print(f"{_ts()} git: push rejected (try {attempt + 1}/3): {push.stderr.strip()[-200:]}")
        time.sleep(5)


RESULT_DELAY_S = 180  # games were settled a few minutes after their start


def archive_loop(once: bool = False, push: bool = True) -> None:
    api = GameAPI()
    lb = _lb()
    print(f"{_ts()} archiving released cases into {PAST_DIR}/ (zips from {config.CASES_DIR}); results for team {TEAM!r}; "
          f"{'pushing past-cases/ to origin/main' if push else 'no git push'}")
    first_pass = True
    while True:
        try:
            games = sorted(((g["id"], _parse(g["start_time"])) for g in api.list_games()), key=lambda x: x[1])
        except Exception as e:  # noqa: BLE001
            print(f"{_ts()} list failed: {e!r}")
            time.sleep(30)
            continue
        now = datetime.now(timezone.utc)
        changed: list[str] = []
        for gid, start in games:
            if start <= now:
                try:
                    if not (PAST_DIR / f"case_{gid:03d}").exists() and archive_case(api, gid):
                        changed.append(f"case {gid}")
                except Exception as e:  # noqa: BLE001 - one bad case must not stop the loop
                    print(f"{_ts()} game {gid}: FAILED {e!r}")
        pending = [gid for gid, st in games if gid != 0 and st <= now
                   and (PAST_DIR / f"case_{gid:03d}").exists()
                   and not (PAST_DIR / f"case_{gid:03d}" / "results.json").exists()]
        if pending:
            try:
                completed = _completed_games(lb)
                for gid in pending:
                    if gid in completed and save_results(lb, gid):
                        changed.append(f"results {gid}")
            except Exception as e:  # noqa: BLE001
                print(f"{_ts()} results FAILED {e!r}")
        if push and (changed or first_pass):  # the first pass also pushes anything archived earlier
            try:
                push_cases("Archive past cases: " + (", ".join(changed) or "backfill"))
            except Exception as e:  # noqa: BLE001 - a git problem must not stop the archive
                print(f"{_ts()} git: push FAILED {e!r}")
        first_pass = False
        if once:
            return
        now = datetime.now(timezone.utc)
        wakes = [st + timedelta(seconds=s) for _, st in games for s in (5, RESULT_DELAY_S)]
        future = [w for w in wakes if w > now]
        still_pending = [gid for gid, st in games if gid != 0 and st <= now
                         and not (PAST_DIR / f"case_{gid:03d}" / "results.json").exists()]
        if still_pending:  # results not settled yet: look again in two minutes
            future.append(now + timedelta(seconds=120))
        if not future:
            print(f"{_ts()} no more games; done")
            return
        nxt = min(future)
        print(f"{_ts()} next check at {nxt.astimezone():%H:%M:%S} (in {(nxt - now).total_seconds() / 60:.1f} min)")
        time.sleep(max((nxt - now).total_seconds(), 1))
