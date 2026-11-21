"""Running one case: estimate -> price -> (optionally) submit, with logging."""

import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path

from . import config
from .case import Case, extract_zip, load_case
from .estimator import estimate
from .pricing import LinePrice, price_case
from .schema import CaseEstimate


def save_run(tag: str, case: Case, est: CaseEstimate, prices: list[LinePrice], meta: dict) -> Path:
    config.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = config.RUNS_DIR / f"{stamp}_{tag}_{meta.get('effort', 'x')}.json"
    path.write_text(json.dumps({
        "tag": tag,
        "case_dir": str(case.case_dir),
        "meta": meta,
        "estimate": est.model_dump(),
        "prices": [p.as_dict() for p in prices],
    }, indent=2, ensure_ascii=False))
    return path


def print_table(est: CaseEstimate, prices: list[LinePrice]) -> None:
    by_idx = {l.index: l for l in est.lines}
    print(f"\n{est.damage_summary}\nPolicy: {est.policy_notes}\n")
    print(f"{'#':>3}  {'q':>5}  {'t_med':>10}  {'a':>10}  {'b':>10}  item")
    for p in prices:
        l = by_idx[p.index]
        print(f"{p.index:>3}  {p.q:>5.2f}  {p.t_median:>10.2f}  {p.a:>10.2f}  {p.b:>10.2f}  {l.invoice_text[:60]}")
        print(f"{'':>45}{l.rationale[:120]}")


def run_local(path: Path, password: str | None, effort: str) -> list[LinePrice]:
    """Estimate a case from a directory or an encrypted zip, without submitting."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        if password is None:
            raise SystemExit("--password is required for a zip")
        path = extract_zip(path, password, config.WORK_DIR / path.stem)
    case = load_case(path)
    est, meta = estimate(case, effort)
    prices = price_case(est)
    print_table(est, prices)
    print(f"\nlatency {meta['latency_s']}s, log: {save_run(path.name, case, est, prices, meta)}")
    return prices


def play_round(game_id: str, zip_path: Path, dry_run: bool = False, key: str | None = None) -> None:
    """Full round: key -> decrypt -> race fast/full estimates -> submit.

    The fast estimate is submitted as soon as it arrives (if the full one isn't
    there yet); the full estimate overwrites it. We stop waiting shortly before
    the 60 s deadline.
    """
    from .api import GameAPI

    api = GameAPI()
    t0 = time.monotonic()
    deadline = t0 + config.ROUND_SECONDS - config.SAFETY_MARGIN_S

    if key is None:
        key = api.get_key(game_id)
    case_dir = extract_zip(Path(zip_path), key, config.WORK_DIR / f"game_{game_id}")
    case = load_case(case_dir)
    print(f"[{time.monotonic() - t0:5.1f}s] case loaded: {case_dir} ({len(case.images)} images)")

    efforts = [config.EFFORT]
    if config.FAST_EFFORT and config.FAST_EFFORT != config.EFFORT:
        efforts.append(config.FAST_EFFORT)

    pool = ThreadPoolExecutor(max_workers=len(efforts))
    futures = {pool.submit(estimate, case, e): e for e in efforts}
    full_done = False
    pending = set(futures)
    try:
        while pending and not full_done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print(f"[{time.monotonic() - t0:5.1f}s] deadline reached, still pending: {[futures[f] for f in pending]}")
                break
            done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
            for fut in done:
                effort = futures[fut]
                try:
                    est, meta = fut.result()
                except Exception as e:  # noqa: BLE001 - keep the round alive
                    print(f"[{time.monotonic() - t0:5.1f}s] {effort} failed: {e!r}")
                    continue
                prices = price_case(est)
                log = save_run(f"game{game_id}", case, est, prices, meta)
                is_full = effort == config.EFFORT
                if dry_run:
                    print(f"[{time.monotonic() - t0:5.1f}s] {effort}: dry run, not submitting ({log})")
                else:
                    try:
                        api.submit(game_id, prices)
                        print(f"[{time.monotonic() - t0:5.1f}s] {effort}: submitted {len(prices)} lines ({log})")
                    except Exception as e:  # noqa: BLE001 - try again with the next estimate
                        print(f"[{time.monotonic() - t0:5.1f}s] {effort}: SUBMIT FAILED {e!r} ({log})")
                        if effort == config.EFFORT:
                            try:
                                api.submit(game_id, prices)
                                print(f"[{time.monotonic() - t0:5.1f}s] {effort}: retry submitted")
                            except Exception as e2:  # noqa: BLE001
                                print(f"[{time.monotonic() - t0:5.1f}s] {effort}: retry failed {e2!r}")
                if is_full:
                    full_done = True
                    print_table(est, prices)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
