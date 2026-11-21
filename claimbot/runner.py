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


def start_memory(case: Case, case_path=None, game_id=None):
    """Kick off the memory query in its worker right after load_case (None when CLAIMS_MEMORY is off). Only games
    before this one are used: live via game_id (the archive stores the running game seconds after its start), for an
    old case from past-cases/case_NNN via its number, so a re-estimate never sees its own outcome."""
    if not config.MEMORY:
        return None
    try:
        from . import memory
        g = memory.game_of(case_path) if case_path is not None else None
        if game_id is not None and str(game_id).isdigit():
            g = int(game_id)
        return memory.get().submit(case, until=None if g is None else g - 1)
    except Exception as e:  # noqa: BLE001 - the memory must never cost the round
        print(f"memory: query not started ({e!r})")
        return None


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
    mem = start_memory(case, path)
    refs = None
    if mem is not None:
        from . import memory
        refs, info = memory.wait_block(mem, time.monotonic() + 30)  # local run: no round clock, wait for the block
        print(f"memory: {info}\n{refs or '(no hint block)'}\n")
    est, meta = estimate(case, effort, references=refs)
    if mem is not None:
        meta["memory"] = memory.summary(mem)
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
    print(f"[{time.monotonic() - t0:5.1f}s] case loaded: {case_dir} ({len(case.image_blobs)} images)")

    efforts = [config.EFFORT]
    if config.FAST_EFFORT and config.FAST_EFFORT != config.EFFORT:
        efforts.append(config.FAST_EFFORT)

    mem = start_memory(case, game_id=game_id)
    until = time.monotonic() + config.MEMORY_BUDGET_S

    def run_effort(e):
        if mem is None:
            return estimate(case, e)
        from . import memory
        if e == config.FAST_EFFORT and len(efforts) > 1:  # the fast call is the bypass: it never waits
            est, meta = estimate(case, e)
            meta["memory"] = dict(used=False, status="bypass")
            return est, meta
        block, info = memory.wait_block(mem, until)
        est, meta = estimate(case, e, references=block)
        meta["memory"] = info
        return est, meta

    pool = ThreadPoolExecutor(max_workers=len(efforts))
    futures = {pool.submit(run_effort, e): e for e in efforts}
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


# --- Ensemble ---------------------------------------------------------------

def save_ensemble_run(tag: str, case: Case, results, failures, timed_out, prices: list[LinePrice],
                      game_id: str | None = None, extra: dict | None = None) -> Path:
    config.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = config.RUNS_DIR / f"{stamp}_{tag}_ensemble.json"
    rec = {
        "tag": tag,
        "case_dir": str(case.case_dir),
        "members": [
            {"member": m.name, "weight": m.weight, "meta": meta, "estimate": est.model_dump(),
             "prices": [p.as_dict() for p in price_case(est)]}
            for m, est, meta in results
        ],
        "failures": [{"member": m.name, "error": err} for m, err in failures],
        "timed_out": [m.name for m in timed_out],
        "prices": [p.as_dict() for p in prices],
        **(extra or {}),
    }
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    if game_id is not None and str(game_id) != "0":  # live round (not test game 0): also goes into the tracked outputs file
        try:
            from . import outputs
            outputs.record(game_id, rec["members"], rec["failures"], rec["timed_out"], rec["prices"])
            print(f"outputs: game {game_id} written to {outputs.OUTPUTS_FILE}")
        except Exception as e:  # noqa: BLE001 - bookkeeping must not break the loop
            print(f"outputs: could not write game {game_id}: {e!r}")
    return path


def _print_ensemble(results, prices: list[LinePrice]) -> None:
    if not results:
        return
    names = {}
    for _, est, _ in results:
        for l in est.lines:
            names.setdefault(l.index, l.invoice_text)
    print(f"\n{'#':>3}  {'q':>5}  {'t_med':>10}  {'sigma':>5}  {'a':>10}  {'b':>10}  item")
    for p in prices:
        print(f"{p.index:>3}  {p.q:>5.2f}  {p.t_median:>10.2f}  {p.sigma:>5.2f}  {p.a:>10.2f}  {p.b:>10.2f}  {names.get(p.index, '')[:55]}")
    print("\nper-member median gross total by line:")
    for m, est, meta in sorted(results, key=lambda r: -r[0].weight):
        meds = {p.index: p.t_median for p in price_case(est)}
        cells = "  ".join(f"{meds.get(p.index, float('nan')):>9.2f}" for p in prices)
        print(f"  {m.name:<28} w={m.weight:<4} {meta['latency_s']:>5.1f}s  {cells}")


def run_local_ensemble(path: Path, password: str | None) -> list[LinePrice]:
    from . import ensemble
    path = Path(path)
    if path.suffix.lower() == ".zip":
        if password is None:
            raise SystemExit("--password is required for a zip")
        path = extract_zip(path, password, config.WORK_DIR / path.stem)
    case = load_case(path)
    t0 = time.monotonic()
    mem = start_memory(case, path)
    t_first = []

    def on_update(prices, done, total, m, est, meta):
        t_first.append(round(time.monotonic() - t0, 2))
        print(f"[{time.monotonic() - t0:5.1f}s] {done}/{total} {m.name} ({meta['latency_s']}s, memory {meta.get('memory', {}).get('status', 'off')})")

    ms = ensemble.members()
    print(f"{len(ms)} members: {', '.join(m.name for m in ms)}")
    results, failures, timed_out = ensemble.run(case, t0 + config.ROUND_SECONDS - config.SAFETY_MARGIN_S, on_update, ms,
                                                references=mem)
    for m, err in failures:
        print(f"FAILED {m.name}: {err[:200]}")
    for m in timed_out:
        print(f"TIMED OUT {m.name}")
    prices = ensemble.combine([(est, m.weight) for m, est, _ in results])
    _print_ensemble(results, prices)
    extra = dict(t_first_estimate_s=t_first[0] if t_first else None, memory=_mem_summary(mem))
    print(f"\nfirst estimate after {extra['t_first_estimate_s']}s; memory {(extra['memory'] or {}).get('status', 'off')}")
    print(f"log: {save_ensemble_run(path.name, case, results, failures, timed_out, prices, extra=extra)}")
    return prices


def _mem_summary(mem):
    if mem is None:
        return None
    from . import memory
    return memory.summary(mem)


def play_round_ensemble(game_id: str, zip_path: Path, dry_run: bool = False, key: str | None = None) -> None:
    """Like play_round, but submits the combined ensemble after every finished member."""
    from . import ensemble
    from .api import GameAPI

    api = GameAPI()
    t0 = time.monotonic()
    deadline = t0 + config.ROUND_SECONDS - config.SAFETY_MARGIN_S
    if key is None:
        key = api.get_key(game_id)
    case_dir = extract_zip(Path(zip_path), key, config.WORK_DIR / f"game_{game_id}")
    case = load_case(case_dir)
    mem = start_memory(case, game_id=game_id)
    try:
        from . import refs
        case.refs = refs.block(exclude_game=game_id, case=case)
    except Exception as e:  # noqa: BLE001 - references are optional
        print(f"refs: not used ({e!r})")
    ms = ensemble.members()
    print(f"[{time.monotonic() - t0:5.1f}s] case loaded: {case_dir} ({len(case.image_blobs)} images), {len(ms)} members"
          + (", memory on" if mem is not None else ""))
    t_first = []

    def on_update(prices, done, total, m, est, meta):
        t_first.append(round(time.monotonic() - t0, 2))
        tag = f"[{time.monotonic() - t0:5.1f}s] {done}/{total} {m.name}" + (
            f" (memory {meta['memory']['status']})" if "memory" in meta else "")
        if dry_run:
            print(f"{tag}: dry run")
            return
        try:
            api.submit(game_id, prices)
            print(f"{tag}: submitted {len(prices)} lines")
        except Exception as e:  # noqa: BLE001 - the next member will submit again
            print(f"{tag}: SUBMIT FAILED {e!r}")

    results, failures, timed_out = ensemble.run(case, deadline, on_update, ms, references=mem)
    for m, err in failures:
        print(f"  failed {m.name}: {err[:160]}")
    for m in timed_out:
        print(f"  timed out {m.name}")
    prices = ensemble.combine([(est, m.weight) for m, est, _ in results])
    _print_ensemble(results, prices)
    extra = dict(t_first_estimate_s=t_first[0] if t_first else None, memory=_mem_summary(mem))
    print(f"first submittable estimate after {extra['t_first_estimate_s']}s; memory {(extra['memory'] or {}).get('status', 'off')}")
    log = save_ensemble_run(f'game{game_id}', case, results, failures, timed_out, prices, game_id=None if dry_run else game_id,
                            extra=extra)
    print(f"log: {log}")
