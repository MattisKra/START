"""v2: v1 prompt + schema: literal valuation price descriptions + rationale must cite deciding clauses."""

import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _schema import CaseLitCite as SCHEMA  # noqa: E402,F401

_spec = importlib.util.spec_from_file_location("v1", pathlib.Path(__file__).with_name("v1.py"))
_v1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v1)
INSTRUCTIONS = _v1.INSTRUCTIONS
