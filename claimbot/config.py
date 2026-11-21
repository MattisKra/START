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
# Handyman: multiply the computed optimal charge by this (1.0 = no change).
CHARGE_MULT = float(os.getenv("CLAIMS_CHARGE_MULT", "1.0"))
# Floor on log-space spread so the model can't claim false certainty.
MIN_SIGMA = float(os.getenv("CLAIMS_MIN_SIGMA", "0.08"))

# --- Paths -----------------------------------------------------------------
CASES_DIR = ROOT / "cases"  # encrypted zips go here
WORK_DIR = ROOT / "runs" / "extracted"  # decrypted cases (untrusted data)
RUNS_DIR = ROOT / "runs"  # one JSON log per run
