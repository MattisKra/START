"""Render Markdown audit rows. No row or model data is persisted by this script."""
import sys

from account import initialize
from inputs import load


def euro(value):
    return f"{value:,.0f}"


def interval(bounds):
    lo, hi = map(euro, bounds)
    return lo if lo == hi else f"{lo}–{hi}"


def financial(row):
    values = [f'{row["g"]}.{row["p"]} {row["text"]}', euro(row["net"]),
              interval(row["below"]), interval(row["inflated"]), euro(row["accepted"]["inflated"]),
              euro(row["accepted"]["unknown"]), euro(row["penalty"]), interval(row["loss"])]
    print("| " + " | ".join(values) + " |")


def feature(row):
    r = row
    flags = "".join(label for label, on in (("R", r["repair"]), ("B", r["bundle"]), ("A", r["anchor"])) if on)
    played = r["play"]
    if played:
        m, q = played["t_median"], played["q"]
        share = r["share_live"]
        sigma = played["sigma"]
    elif r["readers"][0]:
        rd = r["readers"][0]
        m, q, share, sigma = rd["m"], rd["q"], r["share_luna"], None
    else:
        m, q, share, sigma = None, None, None, None
    qty = f'{r["qty"]:g}'+(" flat" if r["flat"] else "")
    models = [x for x in r["readers"] if x]
    if models:
        trio = "/".join(f'{x["m"]:.0f}' for x in models)
        qf = "/".join(f'{x["justified"]:g}' for x in models) + " · " + "/".join(f'{x["fraction"]:g}' for x in models)
    else:
        trio = qf = "—"
    values = [f'{r["g"]}.{r["p"]}', r["kind"], qty, r["decision"], flags or "—",
              f"{m:.0f} · {q:.2f} · {share:.0%} · " + (f"{sigma:.2f}" if sigma is not None else "—") if m is not None else "—",
              trio, qf]
    print("| " + " | ".join(values) + " |")


if __name__ == "__main__":
    rows = load(sys.argv[1])
    initialize(rows)
    for row in rows:
        (financial if sys.argv[2] == "financial" else feature)(row)
