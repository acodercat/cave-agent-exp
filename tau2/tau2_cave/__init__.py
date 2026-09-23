"""Running tau2-bench with the current CaveAgent release.

Importing this package points tau2 at the domains, tasks and policies of the
checkout we install from. tau2 reads that location at import time and otherwise
resolves it relative to the working directory, so it is set here, before
anything imports tau2 — every entry point in this project comes through here.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT.parent / "third_party" / "tau2-bench" / "data"
os.environ.setdefault("TAU2_DATA_DIR", str(DATA_DIR))

from tau2_cave.agent import AGENT_NAME, Tau2CaveAgent, register  # noqa: E402

__all__ = ["AGENT_NAME", "DATA_DIR", "ROOT", "Tau2CaveAgent", "register"]
