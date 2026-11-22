"""Thin strip: which of our approaches submitted in each round (team timeline, research/live/lb_chart.py)."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
plt.rcParams.update({"font.family": "serif", "font.size": 7})
C = {"single": "#8E94A6", "ens_var": "#B4BCF0", "ens8": "#7C86E6", "ens_ref": "#3F49B5", "agent": "#E0A93E", "multi": "#D9478A"}
P = [(1, 2, "single"), (3, 6, "ens_var"), (7, 11, "ens8"), (12, 17, "ens_ref"), (18, 18, "agent"), (19, 19, "multi"),
     (20, 20, "agent"), (21, 21, "multi"), (22, 100, "agent")]
fig, ax = plt.subplots(figsize=(7.0, 0.42))
for a, b, k in P:
    ax.barh(0, b - a + 1, left=a - 0.5, height=1, color=C[k], lw=0)
ax.set_xlim(0.5, 100.5); ax.set_ylim(-0.5, 0.5); ax.set_yticks([])
ax.set_xticks([1, 10, 18, 22, 40, 60, 80, 100]); ax.tick_params(axis="x", length=2, pad=1)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.set_xlabel("round", labelpad=1)
fig.tight_layout(pad=0.1); fig.savefig("figures/approach_strip.pdf"); fig.savefig("figures/approach_strip.png", dpi=200)
