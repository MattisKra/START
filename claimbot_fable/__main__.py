"""CLI (default is DRY-RUN; pass --live to submit; only ONE process may submit):

    uv run python -m claimbot_fable selftest                                   # engine checks, no network
    uv run python -m claimbot_fable estimate CASE_DIR_OR_ZIP [--password PW] [--reader SPEC]   # read one case, never submits
    uv run python -m claimbot_fable round GAME_ID --zip cases/case_017.zip [--live]      # or --case-dir DECRYPTED_DIR for a dry-run test
    uv run python -m claimbot_fable watch [--live]                              # whole tournament loop, like `claimbot watch`
    uv run python -m claimbot_fable replay LOG.json                             # recompute a saved round with the current FABLE_* values

Reader specs: provider:model:effort[:noimage] (see readers.py). Override with FABLE_FAST / FABLE_MAIN / FABLE_STANDBY;
multipliers with FABLE_KA_OPEN, FABLE_KB_OPEN, FABLE_KA_PINNED, FABLE_KB_PINNED, FABLE_B_ZERO_BELOW, FABLE_EXCLUDED_A (as_valid | zero | 0.5).
"""

import argparse
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI

from . import engine, readers, runner
from .schema import AggregateLimit, Anchor, ReaderCase, ReaderLine


def selftest() -> None:
    """Hand-checked cases for the rule engine (no network)."""
    def line(i, qty=1, p50=100.0, q=0.95, frac=1.0, inv=None):
        return ReaderLine(index=i, invoice_text=f"l{i}", unit="pcs", quantity_invoiced=inv or qty, quantity_justified=qty, covered=True,
                          related=True, p_valid=q, net_unit_price_p10=p50 * 0.7, net_unit_price_p50=p50, net_unit_price_p90=p50 * 1.4,
                          vat_rate=0.19, payout_fraction=frac, rationale="")
    P = engine.Params(ka_open=0.9, kb_open=1.25, ka_pinned=0.85, kb_pinned=1.05, b_zero_below=2 / 3, excluded_below=0.5, excluded_a="as_valid")
    est = ReaderCase(damage_summary="", policy_notes="", lines=[line(0, p50=100), line(1, p50=100, frac=0.5), line(2, p50=100, q=0.02)],
                     aggregate_limits=[], anchors=[])
    o = engine.compute(est, P)
    assert abs(o[0].m - 119.0) < 1e-6 and abs(o[0].a - 107.1) < 0.01 and abs(o[0].b - 148.75) < 0.01, o[0]        # 100 x 1.19, KA 0.9, KB 1.25
    assert abs(o[1].m - 59.5) < 1e-6, o[1]                                                                        # halving
    assert o[2].b == 0 and o[2].a > 0, o[2]                                                                         # excluded: b = 0, free option a
    est2 = est.model_copy(update={"lines": [line(0, p50=1000), line(1, p50=1000)], "aggregate_limits": [AggregateLimit(amount_gross=1190, line_indices=[0, 1], clause="x")]})
    o = engine.compute(est2, P)
    assert abs(o[0].m + o[1].m - 1190) < 0.01 and o[0].pinned and abs(o[0].a - 0.85 * 595) < 0.01, o                  # rateable, pinned multipliers
    est3 = est.model_copy(update={"lines": [line(0, p50=500), line(1, p50=200)], "anchors": [Anchor(total_gross=1000, line_indices=[0, 1], kind="total", quote="x")]})
    o = engine.compute(est3, P)
    assert abs(o[0].m + o[1].m - 1000) < 0.01, o                                                                    # anchor: scaled to the stated total
    est4 = est.model_copy(update={"lines": [line(0, qty=1, inv=3, p50=100)]})
    assert abs(engine.compute(est4, P)[0].m - 119.0) < 1e-6                                                         # justified quantity 1 of 3
    assert engine.printed_positions("  1   Foo bar    2   pcs\n  2   Baz   1 pcs\n") == [1, 2]
    print("selftest ok: multipliers, halving, excluded line, rateable limit, anchor, justified quantity, POS parsing")


def watch(live: bool) -> None:
    from claimbot.watch import _parse, _ts, _wait_for_key
    api = GameAPI()
    done: set[int] = set()
    print(f"{_ts()} claimbot_fable watching ({'LIVE: submitting' if live else 'DRY-RUN: not submitting'}); readers: "
          + ", ".join(f"{k}={v.name}" for k, v in runner.default_specs().items()))
    while True:
        try:
            games = api.list_games()
        except Exception as e:  # noqa: BLE001
            print(f"{_ts()} list failed: {e!r}"); time.sleep(10); continue
        now = datetime.now(timezone.utc)
        upcoming = sorted(((g["id"], _parse(g["start_time"])) for g in games if g["id"] != 0 and g["id"] not in done), key=lambda x: x[1])
        upcoming = [(gid, st) for gid, st in upcoming if (now - st).total_seconds() < config.ROUND_SECONDS - 15]
        if not upcoming:
            print(f"{_ts()} no upcoming games; checking again in 60 s"); time.sleep(60); continue
        gid, start = upcoming[0]
        wait_s = (start - now).total_seconds()
        if wait_s > 90:
            m, sec = divmod(int(round(wait_s)), 60)
            print(f"{_ts()} next: game {gid} at {start.astimezone():%H:%M:%S} (in {m}m {sec:02d}s)")
            time.sleep(min(wait_s - 60, 60)); continue
        zip_path = config.CASES_DIR / f"case_{gid:03d}.zip"
        done.add(gid)
        if not zip_path.exists():
            print(f"{_ts()} game {gid}: MISSING {zip_path}"); continue
        key = _wait_for_key(api, gid, start)
        if key is None:
            print(f"{_ts()} game {gid}: NO KEY after 30 s, skipping"); continue
        try:
            runner.play_round_fable(str(gid), zip_path, key=key, start=start, live=live)
        except Exception:  # noqa: BLE001 - one bad round must not kill the loop
            print(f"{_ts()} game {gid}: ROUND FAILED\n{traceback.format_exc()}")


def replay(path: Path) -> None:
    rec = json.loads(Path(path).read_text())
    tiers = rec.get("tiers") or {"main": {"estimate": rec["estimate"]}}
    for name, t in tiers.items():
        est = ReaderCase.model_validate(t["estimate"])
        lines = engine.compute(est)
        print(f"== {name}")
        runner.print_table(est, lines)


def main() -> None:
    ap = argparse.ArgumentParser(prog="claimbot_fable")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    e = sub.add_parser("estimate"); e.add_argument("path"); e.add_argument("--password"); e.add_argument("--reader")
    r = sub.add_parser("round"); r.add_argument("game_id"); r.add_argument("--zip"); r.add_argument("--case-dir", help="already decrypted case folder (dry-run test only)"); r.add_argument("--live", action="store_true")
    w = sub.add_parser("watch"); w.add_argument("--live", action="store_true")
    p = sub.add_parser("replay"); p.add_argument("log")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "estimate":
        spec = readers.parse_spec(a.reader) if a.reader else runner.default_specs()["main"]
        runner.run_local(Path(a.path), a.password, spec)
    elif a.cmd == "round":
        runner.play_round_fable(a.game_id, Path(a.zip) if a.zip else None, live=a.live, case_dir=Path(a.case_dir) if a.case_dir else None)
    elif a.cmd == "watch":
        watch(a.live)
    elif a.cmd == "replay":
        replay(Path(a.log))


if __name__ == "__main__":
    main()
