"""Append-only local revisions and the receipt time relative to the official release."""
import json
import math
import time
from pathlib import Path


def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    tmp.replace(path)


class Trace:
    def __init__(self, folder: Path, arm: str, start: float, positions):
        self.path = folder / f"{arm}.jsonl"
        self.start = start
        self.positions = set(positions)
        self.previous = {}
        self.last_on_time = None

    def log(self, kind, **fields):
        elapsed = time.time() - self.start
        row = dict(event=kind, elapsed_s=round(elapsed, 4), on_time=0 <= elapsed <= 60, **fields)
        with self.path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        return row

    def record(self, lines, trigger):
        snapshot = {}
        for line in lines:
            pos = line["index"]
            if type(pos) is not int or pos not in self.positions or pos in snapshot:
                raise ValueError(f"Unexpected or duplicate position {pos}")
            amounts = [line[k] for k in ("charge_price", "acceptance_limit")]
            if not all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in amounts):
                raise ValueError(f"Invalid price on position {pos}")
            snapshot[pos] = dict(zip(("charge_price", "acceptance_limit"), amounts))
        if snapshot.keys() != self.positions:
            raise ValueError("Revision does not cover every printed position")
        changes = [dict(index=p, before=self.previous.get(p), after=v)
                   for p, v in snapshot.items() if self.previous.get(p) != v]
        row = self.log("decision", trigger=trigger, changes=changes, lines=lines)
        self.previous = snapshot
        if row["on_time"]:
            self.last_on_time = row
