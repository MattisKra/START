"""One round (review section E5/E6): three reads in parallel, priority-ordered submit, never overwrite a better answer with a worse one.

  T+0      key, decrypt, start fast / main / standby at once
  by T+15  fast tier answers  -> submit (tier 1)
  by T+40  main reader answers -> rule engine -> submit (tier 3, overwrites)
  T+45     main still missing -> submit the standby's answer (tier 2)
  T+52     last possible submit; nothing after it.    No answer by T+30 -> ALERT printed.
Priority: main (3) > standby (2) > fast (1). DRY-RUN unless live=True.
"""

import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.case import Case, extract_zip, load_case
from claimbot.pricing import LinePrice

from . import engine, readers

FABLE_RUNS = config.RUNS_DIR / "fable"
STANDBY_AT, LAST_SUBMIT, ALERT_AT = 45.0, 52.0, 30.0
TIER = {"fast": 1, "standby": 2, "main": 3}


def default_specs() -> dict[str, readers.Spec]:
    """Reader specs, overridable with FABLE_FAST / FABLE_MAIN / FABLE_STANDBY. Falls back to OpenRouter when a native key is missing."""
    have = lambda k: bool(os.getenv(k))
    orr = have("OPENROUTER_API_KEY")
    main = os.getenv("FABLE_MAIN") or ("anthropic:claude-fable-5-2:low" if have("ANTHROPIC_API_KEY") else
                                       "openrouter:anthropic/claude-fable-5.2:low" if orr else "openai:gpt-6.1-terra:medium")
    standby = os.getenv("FABLE_STANDBY") or ("openai:gpt-6.1-terra:medium" if (config.OPENAI_KEY) else
                                              "openrouter:openai/gpt-6.1-terra:medium" if orr else "")
    fast = os.getenv("FABLE_FAST") or ("openai:gpt-6-luna:low:noimage" if config.OPENAI_KEY else
                                        "openrouter:openai/gpt-6-luna:low:noimage" if orr else "")
    out = {"main": readers.parse_spec(main)}
    if standby:
        out["standby"] = readers.parse_spec(standby)
    if fast:
        out["fast"] = readers.parse_spec(fast)
    return out


def to_prices(est, case: Case, params=None):
    lines = engine.compute(est, params)
    pos, warns = engine.check(est, case.invoice_text)
    order = {l.index: i for i, l in enumerate(sorted(est.lines, key=lambda l: l.index))}
    prices = [LinePrice(pos[order[x.index]] - config.INDEX_BASE, x.a, x.b, x.m, x.q, 0.0) for x in lines]
    return lines, prices, warns


def print_table(est, lines, warns=()):
    by = {l.index: l for l in est.lines}
    print(f"\n{est.damage_summary}\nPolicy: {est.policy_notes[:300]}")
    for w in warns:
        print(f"  WARNING: {w}")
    for lim in est.aggregate_limits:
        print(f"  limit {lim.amount_gross:g} on lines {lim.line_indices}: {lim.clause[:80]}")
    for an in est.anchors:
        print(f"  anchor {an.kind} {an.total_gross:g} on lines {an.line_indices}: \"{an.quote[:80]}\"")
    print(f"{'#':>2} {'q':>5} {'qty':>7} {'frac':>5} {'m':>9} {'a':>9} {'b':>9} pin  item")
    for x in lines:
        l = by[x.index]
        print(f"{x.index + 1:>2} {x.q:>5.2f} {l.quantity_justified:>3g}/{l.quantity_invoiced:<3g} {l.payout_fraction:>5.2f} {x.m:>9.2f} {x.a:>9.2f} {x.b:>9.2f} "
              f"{'P' if x.pinned else ' '}    {l.invoice_text[:44]}  {x.note}")
        print(f"{'':>52}{l.rationale[:110]}")


def save_log(tag: str, record: dict) -> Path:
    FABLE_RUNS.mkdir(parents=True, exist_ok=True)
    path = FABLE_RUNS / f"{datetime.now():%Y%m%d-%H%M%S}_{tag}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False, default=str))
    return path


def run_local(path: Path, password: str | None, spec: readers.Spec) -> None:
    """Read one case with one reader and print the table. Never submits."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        if password is None:
            raise SystemExit("--password is required for a zip")
        path = extract_zip(path, password, config.WORK_DIR / path.stem)
    case = load_case(path)
    est, meta = readers.read(case, spec)
    lines, prices, warns = to_prices(est, case)
    print_table(est, lines, warns)
    print(f"\n{spec.name}: {meta['latency_s']}s  usage {meta['usage']}")
    print(f"log: {save_log(path.name, dict(meta=meta, estimate=est.model_dump(), lines=[x.as_dict() for x in lines]))}")


def play_round_fable(game_id: str, zip_path: Path | None, key: str | None = None, start: datetime | None = None, live: bool = False,
                     case_dir: Path | None = None) -> None:
    """case_dir: an already decrypted case folder (testing; skips key and 7-Zip). Never combine case_dir with live=True."""
    if case_dir is not None and live:
        raise SystemExit("--case-dir is for dry-run tests only")
    api = GameAPI() if live else None
    t_wall = time.monotonic()
    if case_dir is not None:
        case = load_case(Path(case_dir))
    else:
        api = api or GameAPI()
        key = key or api.get_key(game_id)
        case = load_case(extract_zip(Path(zip_path), key, config.WORK_DIR / f"fable_game_{game_id}"))
    # T0 is the SERVER round start when known (so a late process does not get a longer minute), else now.
    t0 = time.monotonic()
    if start is not None:
        t0 -= max((datetime.now(timezone.utc) - start).total_seconds(), 0.0)
    now = lambda: time.monotonic() - t0
    specs = default_specs()
    print(f"[{now():5.1f}s] game {game_id}: case loaded ({len(case.image_blobs)} photos); readers: " + ", ".join(f"{k}={v.name}" for k, v in specs.items())
          + ("  LIVE" if live else "  DRY-RUN"))
    pool = ThreadPoolExecutor(max_workers=len(specs))
    futs = {pool.submit(readers.read, case, s, k == "fast"): k for k, s in specs.items()}
    pending, results, failures = set(futs), {}, {}
    best_submitted, alerted = 0, False
    record = dict(game=game_id, live=live, readers={k: v.name for k, v in specs.items()}, submits=[], tiers={}, failures={})

    def submit(tier_name: str):
        nonlocal best_submitted
        est, meta = results[tier_name]
        lines, prices, warns = to_prices(est, case)
        for w in warns:
            print(f"[{now():5.1f}s] WARNING {w}")
        record["tiers"][tier_name] = dict(meta=meta, estimate=est.model_dump(), lines=[x.as_dict() for x in lines])
        ok = False
        if live:
            for attempt in (1, 2):
                try:
                    api.submit(game_id, prices); ok = True; break
                except Exception as e:  # noqa: BLE001
                    print(f"[{now():5.1f}s] {tier_name}: SUBMIT FAILED {e!r} (try {attempt})")
        else:
            ok = True
        if ok:
            best_submitted = max(best_submitted, TIER[tier_name])
            record["submits"].append(dict(tier=tier_name, t=round(now(), 1), n=len(prices), live=live))
            print(f"[{now():5.1f}s] {tier_name}: {'submitted' if live else 'dry-run (not submitted)'} {len(prices)} lines  a={[p.a for p in prices]} b={[p.b for p in prices]}")

    try:
        while now() < LAST_SUBMIT:
            done, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
            for f in done:
                k = futs[f]
                try:
                    results[k] = f.result()
                    print(f"[{now():5.1f}s] {k} answered in {results[k][1]['latency_s']}s")
                except Exception as e:  # noqa: BLE001
                    failures[k] = repr(e)[:300]; print(f"[{now():5.1f}s] {k} FAILED {e!r}")
            main_running = any(futs[f] == "main" for f in pending)
            for k in ("main", "standby", "fast"):                       # priority order
                if k in results and TIER[k] > best_submitted:
                    if k == "standby" and main_running and now() < STANDBY_AT:
                        continue                                           # hold: the main reader may still arrive
                    submit(k)
            if best_submitted == 0 and not alerted and now() > ALERT_AT:
                alerted = True; print(f"[{now():5.1f}s] ALERT: nothing submitted after {ALERT_AT:.0f} s")
            if not pending and (best_submitted == TIER["main"] or ("main" in failures and best_submitted > 0)):
                break
            if not pending:
                break
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if best_submitted == 0:
        print(f"[{now():5.1f}s] ALERT: ROUND ENDED WITH NO SUBMISSION (failures: {failures})")
    record["failures"] = failures
    record["best_tier"] = best_submitted
    print(f"[{now():5.1f}s] done (best tier {best_submitted}); wall since start of call {time.monotonic() - t_wall:.1f}s; log: {save_log(f'game{game_id}', record)}")
