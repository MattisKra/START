"""Settings. Everything can be overridden via environment variables or .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- LLM -------------------------------------------------------------------
MODEL = os.getenv("CLAIMS_MODEL", "gpt-6-luna")
EFFORT = os.getenv("CLAIMS_EFFORT", "medium")
# A cheaper second call that runs in parallel, so we have something to submit
# early if the medium-effort call is slow.
FAST_EFFORT = os.getenv("CLAIMS_FAST_EFFORT", "low")
OPENAI_KEY = os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
# Run the weighted multi-model ensemble (claimbot/ensemble.py) instead of one model.
USE_ENSEMBLE = os.getenv("CLAIMS_USE_ENSEMBLE", "1") == "1"
LLM_TIMEOUT_S = float(os.getenv("CLAIMS_LLM_TIMEOUT", "50"))

# --- Game API --------------------------------------------------------------
TEAM_API_KEY = os.getenv("TEAM_API_KEY")
API_BASE = os.getenv("CLAIMS_API_BASE", "https://c2f.public.quantco.cloud")
# Index of the first invoice line in the submission. The deep-dive slide
# example uses 1, 2, ...; confirm against API_HANDBOOK.md / Game 0.
INDEX_BASE = int(os.getenv("CLAIMS_INDEX_BASE", "1"))
ROUND_SECONDS = 60
# Stop waiting for the slow model this many seconds before the deadline.
SAFETY_MARGIN_S = 6

# --- Strategy --------------------------------------------------------------
# Insurer: reject a charge when P(charge is inflated) exceeds this.
# 1/3 is the break-even from the payoff matrix (1.5a * (1-p) < a).
REJECT_P = float(os.getenv("CLAIMS_REJECT_P", str(1 / 3)))
# Insurer: for lines we believe are valid (P(invalid) below REJECT_P), accept
# up to at least this multiple of our median. Games 1-3 showed our medians
# run low and the 1/3-quantile rejected many fair charges.
B_VALID_MULT = float(os.getenv("CLAIMS_B_VALID_MULT", "1.25"))
# Handyman: multiply the computed optimal charge by this (1.0 = no change).
CHARGE_MULT = float(os.getenv("CLAIMS_CHARGE_MULT", "1.0"))
# Ensemble charge as a multiple of the combined median. Replay on games 1-6: 0.9 gave 40,302 against 34,249 for the
# argmax rule (about 0.75 x median); see research/ensemble_analysis/fable_vs_ensemble.py. 0 switches back to the argmax rule.
A_MEDIAN_MULT = float(os.getenv("CLAIMS_A_MEDIAN_MULT", "0.9"))
# Acceptance limit as a multiple of our combined median (valid lines only; b stays 0 where the line is probably invalid).
# Set to 0.55 from the audited euro replay of the reviewer COST side (research/bench/limit_sweep.py, README 17:15 and 17:35).
# Money saved against what we actually paid, by factor (live medians games 1-9 | cheap-reader medians games 1-15):
#   0.45: +18.3k | +24.3k   0.55: +17.4k | +22.5k..23.1k   0.6: +16.0k | +21.8k..23.2k   0.8: +6.5k | +12.2k..15.6k
#   0.9-1.0: +4.5k..6.2k | +8.2k..12.3k   1.25: 0..+3.5k | +4.0k..10.6k.   Cost falls steeply between 0.8 and 0.6 (the field's fair
# charges cluster at about 0.7-0.8 of the value) and is flat below 0.6. 0.55 sits safely below that cliff.
# Regime dependence: in fair-heavy stretches (games 1-6) a strict limit costs about 1-2k per six games (penalties for rejecting fair
# charges); in over-charging stretches (games 7-10) it saves about 22-25k; in the latest 5 games about 1-2k. A fixed value is as good
# as an adaptive one (+0.6k over 14 games). Cost side only: the evaluator cannot measure the charge side.
# 0 switches back to the quantile rule with the B_VALID_MULT floor.
B_MEDIAN_MULT = float(os.getenv("CLAIMS_B_MEDIAN_MULT", "0.55"))
# Floor on log-space spread so the model can't claim false certainty.
MIN_SIGMA = float(os.getenv("CLAIMS_MIN_SIGMA", "0.08"))

# --- Case memory (claimbot/memory.py) ----------------------------------------
# Hints from earlier, settled games in the prompt. OFF by default: switch it on only after the forward evaluation
# (research/bench/rag_bench.py --retriever memory --forward) shows a gain and the first submission is not later.
MEMORY = os.getenv("CLAIMS_MEMORY", "0") == "1"
MEMORY_K = int(os.getenv("CLAIMS_MEMORY_K", "3"))  # neighbours per invoice line
MEMORY_MIN_SCORE = float(os.getenv("CLAIMS_MEMORY_MIN_SCORE", "0.25"))
# Members outside the bypass wait at most this long for the hint block; after that they run without it.
MEMORY_BUDGET_S = float(os.getenv("CLAIMS_MEMORY_BUDGET_S", "0.5"))
# Members (names like "gpt-6.1-terra/low") that always start at once without hints. Empty = the low-effort member with
# the smallest median latency in outputs/model_outputs.json.
MEMORY_BYPASS = [s.strip() for s in os.getenv("CLAIMS_MEMORY_BYPASS", "").split(",") if s.strip()]
# `claimbot archive` rebuilds the memory after each game's results (one cheap LLM call per new case).
MEMORY_AUTOBUILD = os.getenv("CLAIMS_MEMORY_AUTOBUILD", "1") == "1"
MEMORY_MODEL = os.getenv("CLAIMS_MEMORY_MODEL", MODEL)
MEMORY_EFFORT = os.getenv("CLAIMS_MEMORY_EFFORT", "low")
# Which settlement data the memory learns from: "leaderboard" = our own rows plus brackets from ALL teams' public
# leaderboard rows of completed games (runs/bench/labels.jsonl; the organisers confirmed this use on 2026-11-21),
# "own" = only our own rows.
MEMORY_LABELS = os.getenv("CLAIMS_MEMORY_LABELS", "leaderboard")
TEAM = os.getenv("CLAIMS_TEAM", "Kiebler Software Solutions")
LABELS_FILE = ROOT / "runs" / "bench" / "labels.jsonl"

# --- Paths -----------------------------------------------------------------
CASES_DIR = ROOT / "cases"  # encrypted zips go here
WORK_DIR = ROOT / "runs" / "extracted"  # decrypted cases (untrusted data)
RUNS_DIR = ROOT / "runs"  # one JSON log per run
MEMORY_DIR = ROOT / "runs" / "memory"  # versioned memory builds (gitignored: holds settled amounts)
PAST_DIR = ROOT / "past-cases"
