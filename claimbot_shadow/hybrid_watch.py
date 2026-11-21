"""Issue local hybrid receipts over the next three releases, reusing active arms."""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import hybrid
from .__main__ import round_pair
from .trace import Trace, write_json


def read(path):
    return json.loads(path.read_text())


def new_events(path, offsets):
    if not path.exists():
        return
    with path.open("rb") as f:
        f.seek(offsets.get(path, 0))
        for raw in f:
            if not raw.endswith(b"\n"):
                break
            offsets[path] = f.tell()
            yield json.loads(raw)


def observe(game, folder, python_dir, fable_dir):
    start = _parse(game["start_time"]).timestamp()
    offsets = {}
    readers = {}
    trace = None
    fable = None
    while time.time() <= start + 60:
        if trace is None:
            paths = [d / "input.json" for d in (python_dir, fable_dir)]
            if not all(p.exists() for p in paths):
                time.sleep(.05)
                continue
            inputs = [read(p) for p in paths]
            for key in ("game", "release", "positions", "archive_sha256"):
                if inputs[0][key] != inputs[1][key]:
                    raise ValueError(f"Shadow inputs disagree on {key}")
            if inputs[0]["game"] != game["id"] or _parse(inputs[0]["release"]).timestamp() != start:
                raise ValueError("Source game or release differs from frozen schedule")
            write_json(folder / "input.json", inputs[0])
            trace = Trace(folder, "hybrid", start, inputs[0]["positions"])
        updated = False
        for event in new_events(python_dir / "python.jsonl", offsets):
            if event["event"] == "decision" and event["on_time"]:
                readers[event["trigger"]["member"]] = hybrid.reader_values(event)
                updated = True
        for event in new_events(fable_dir / "fable.jsonl", offsets):
            if event["event"] == "decision" and event["on_time"]:
                fable = event
                updated = True
        if updated and fable:
            try:
                choices = hybrid.choose(fable["lines"], readers, trace.positions)
            except ValueError as exc:
                trace.log("invalid_beliefs", error=str(exc))
            else:
                trace.record(choices, dict(fable_write=fable["trigger"]["tool_call"],
                                           fable_elapsed_s=fable["elapsed_s"], readers=sorted(readers)))
        time.sleep(.05)
    final = trace.last_on_time if trace else None
    write_json(folder / "result.json", dict(game=game["id"], status="recorded" if final else "no_on_time_receipt",
                                            final=final))


def start(existing):
    api = GameAPI()
    schedule = api.list_games()
    now = datetime.now(timezone.utc)
    games = sorted((g for g in schedule if g["id"] and _parse(g["start_time"]) > now),
                   key=lambda g: _parse(g["start_time"]))[:3]
    if not games:
        raise SystemExit("No future releases")
    active = read(existing / "manifest.json")["games"] if existing else []
    companions = (read(existing / "verified-fable/manifest.json")["games"]
                  if existing and (existing / "verified-fable/manifest.json").exists() else [])
    root = config.RUNS_DIR / "shadow" / now.strftime("hybrid-%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    for g in games:
        item = {k: g[k] for k in ("id", "start_time")}
        overlap = item in active
        directory = (existing if overlap else root / "paired") / str(g["id"])
        fable_source = existing / "verified-fable" / str(g["id"]) if overlap and item in companions else directory
        g.update(python_dir=str(directory), fable_dir=str(fable_source), reuse=overlap)
    write_json(root / "manifest.json", dict(frozen_at=now.isoformat(), games=games, rule=hybrid.RULE,
               selector_sha256=hashlib.sha256(Path(hybrid.__file__).read_bytes()).hexdigest()))
    print(root, flush=True)
    (root / "paired").mkdir()
    for g in games:
        dest = root / str(g["id"])
        dest.mkdir()
        start_time = _parse(g["start_time"]).timestamp()
        time.sleep(max(0., start_time - time.time() - 1))
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                python_dir, fable_dir = Path(g["python_dir"]), Path(g["fable_dir"])
                job = None if g["reuse"] else pool.submit(round_pair, api, g, python_dir)
                observe(g, dest, python_dir, fable_dir)
                if job:
                    job.result()
        except Exception as exc:
            write_json(dest / "error.json", dict(error=str(exc), exception=type(exc).__name__))
        print("Finished", g["id"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", type=Path, help="Directory of a running paired shadow")
    start(parser.parse_args().reuse)
