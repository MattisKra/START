"""Score completed comparisons with the repo's existing offline metrics."""
import json
from collections import defaultdict
from statistics import mean



def summarize(records):
    from research.bench import bench
    labels = bench.load_labels() if (bench.RUNS / "labels.jsonl").is_file() else {}
    annotations = json.loads((bench.BENCH / "annotations.json").read_text())
    grouped = defaultdict(list)
    for record in records:
        grouped[record["architecture"]].append(record)
    summaries = []
    for count, runs in grouped.items():
        scores = []
        costs = []
        for run in runs:
            attempts = run["attempts"]
            prices = [(a["meta"].get("usage") or {}).get("cost") for a in attempts]
            if prices and all(p is not None for p in prices) and not run.get("timed_out") and not run["errors"]:
                costs.append(sum(prices))
            case = run["case"]
            for line in run["payload"] or []:
                pos = line["index"]
                label = labels.get(case, {}).get(pos)
                if label:
                    scores.append(bench.score_line(dict(a=line["charge_price"], b=line["acceptance_limit"],
                        t_median=line["median"], q=line["probability"]), label,
                        annotations.get(case, {}).get(str(pos), {})))
        summaries.append(dict(readers=count, cases=len(runs), complete=sum(bool(r["payload"]) for r in runs),
            mean_seconds=round(mean(r["total_elapsed_s"] for r in runs), 3),
            mean_provider_cost_usd=mean(costs) if len(costs) == len(runs) else None,
            scored_lines=len(scores), metrics=bench.summarize(scores) if scores else None))
    return summaries
