"""Record paired local decisions on the next three scheduled releases."""
import hashlib
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.case import extract_zip, load_case
from claimbot.watch import _parse, _wait_for_key
from claimbot_multiagent.settlement import invoice_items

from . import fable_arm, python_arm
from .trace import Trace, write_json
from .reasons import save as save_reasons


def compare_lines(receipts):
    if not receipts.get("python") or not receipts.get("fable"):
        return None
    python, fable = ({r["index"]: r for r in receipts[name]["lines"]} for name in ("python", "fable"))
    return [dict(index=p, charge_delta=round(fable[p]["charge_price"] - row["charge_price"], 2),
                 limit_delta=round(fable[p]["acceptance_limit"] - row["acceptance_limit"], 2),
                 fable_evidence=fable[p].get("evidence"), python_reader=row.get("arriving_reader"))
            for p, row in sorted(python.items())]


def round_pair(api, game, folder, arms=None):
    gid, start = game["id"], _parse(game["start_time"])
    folder.mkdir()
    archive = config.CASES_DIR / f"case_{gid:03d}.zip"
    key = _wait_for_key(api, gid, start)
    if not key:
        raise RuntimeError("Release key unavailable")
    with tempfile.TemporaryDirectory(prefix="claims-shadow-input-") as temp:
        case = load_case(extract_zip(archive, key, Path(temp) / "case"))
        positions = [r.position for r in invoice_items(case.invoice_text)]
        write_json(folder / "input.json", dict(game=gid, release=game["start_time"],
                   archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), positions=positions,
                   prepared_s=round(time.time() - start.timestamp(), 4)))
        if arms is None:
            arms = {"python": python_arm.run, "fable": fable_arm.run}
        traces = {name: Trace(folder, name, start.timestamp(), positions) for name in arms}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {name: pool.submit(run, case, traces[name]) for name, run in arms.items()}
            for name, job in jobs.items():
                try:
                    job.result()
                except Exception as exc:
                    traces[name].log("arm_error", exception=type(exc).__name__, detail=str(exc)[:500])
        receipts = {name: trace.last_on_time for name, trace in traces.items()}
        save_reasons(folder)
        write_json(folder / "result.json", dict(game=gid, final=receipts,
                   fable_minus_python=compare_lines(receipts)))


def main():
    api = GameAPI()
    games = api.list_games()
    now = datetime.now(timezone.utc)
    games = sorted((g for g in games if g["id"] and _parse(g["start_time"]) > now),
                   key=lambda g: _parse(g["start_time"]))[:3]
    if not games:
        raise SystemExit("No future games scheduled")
    folder = config.RUNS_DIR / "shadow" / now.strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True)
    write_json(folder / "manifest.json", dict(frozen_at=now.isoformat(),
               games=[{k: g[k] for k in ("id", "start_time")} for g in games]))
    print(folder, [g["id"] for g in games], flush=True)
    for game in games:
        dest = folder / str(game["id"])
        try:
            round_pair(api, game, dest)
        except Exception as exc:
            write_json(dest / "error.json", dict(exception=type(exc).__name__, detail=str(exc)[:500]))
        print(f"Finished game {game['id']}", flush=True)


if __name__ == "__main__":
    main()
