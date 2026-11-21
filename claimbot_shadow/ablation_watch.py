"""Follow an existing hybrid run, applying two frozen rules to each recorded revision."""
import argparse
import hashlib
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.case import extract_zip, load_case
from claimbot.watch import _wait_for_key, _parse
from claimbot_multiagent.settlement import invoice_items
from . import ablations, hybrid
from .hybrid_watch import new_events, read
from .trace import write_json


def observe(root, game):
    gid = game["id"]
    start = _parse(game["start_time"])
    archive = config.CASES_DIR / f"case_{gid:03d}.zip"
    key = _wait_for_key(GameAPI(), gid, start)
    if not key:
        raise ValueError("Release key unavailable")
    with tempfile.TemporaryDirectory() as temp:
        case = load_case(extract_zip(archive, key, Path(temp) / "case"))
        items = {i.position: i for i in invoice_items(case.invoice_text)}
    dest = root / "ablations" / str(gid)
    dest.mkdir()
    source = root / str(gid)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checked = False
    offsets = {}
    with (dest / "decisions.jsonl").open("x") as out:
        while time.time() <= start.timestamp() + 61:
            if not checked and (source / "input.json").exists():
                inp = read(source / "input.json")
                if inp["archive_sha256"] != digest or set(inp["positions"]) != set(items):
                    raise ValueError("Released invoice differs from hybrid inputs")
                checked = True
            if checked:
                for event in new_events(source / "hybrid.jsonl", offsets):
                    if event["event"] != "decision" or not event["on_time"]:
                        continue
                    lines = [ablations.select(row, items[row["index"]]) for row in event["lines"]]
                    if len(lines) != len(items) or {r["index"] for r in lines} != set(items):
                        raise ValueError("Incomplete decision")
                    observed = time.time() - start.timestamp()
                    out.write(json.dumps(dict(source_s=event["elapsed_s"], observed_s=observed,
                                              source_trigger=event["trigger"], lines=lines)) + "\n")
                    out.flush()
            time.sleep(.04)
    write_json(dest / "result.json", dict(game=gid, archive_sha256=digest, checked=checked))


def run(root):
    base = read(root / "manifest.json")
    dest = root / "ablations"
    manifest = dest / "manifest.json"
    sha = hashlib.sha256(Path(ablations.__file__).read_bytes()).hexdigest()
    if not manifest.exists():
        now = datetime.now(timezone.utc)
        games = [g for g in base["games"] if _parse(g["start_time"]) > now]
        if not games:
            raise ValueError("No unreleased games in this hybrid run")
        dest.mkdir(exist_ok=True)
        write_json(manifest, dict(frozen_at=now.isoformat(), games=games, selector_sha256=sha,
                                  hybrid_sha256=base["selector_sha256"]))
    m = read(manifest)
    if m["selector_sha256"] != sha or m["hybrid_sha256"] != hashlib.sha256(Path(hybrid.__file__).read_bytes()).hexdigest():
        raise ValueError("Frozen selector no longer matches source")
    for game in m["games"]:
        if _parse(m["frozen_at"]) >= _parse(game["start_time"]):
            raise ValueError("Rule was frozen after release")
        folder = dest / str(game["id"])
        if folder.exists():
            raise ValueError(f"Existing ablation output: {folder}")
        try:
            observe(root, game)
        except Exception as exc:
            folder.mkdir(exist_ok=True)
            write_json(folder / "error.json", dict(error=str(exc), exception=type(exc).__name__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    run(parser.parse_args().root)
