"""The capability-matched JSON baseline for the τ² experiment (reviewer R3 #3).

A third arm beside ``tau2_cave``: JSON tool calling over the same persistent
Python runtime, so the comparison separates how an action crosses the boundary
from what lies behind it. See ``tau2_json_exec.agent``.

Importing ``tau2_cave`` first is what points tau2 at the frozen checkout's data
directory; it reads that location at import time, so it has to be set before
anything imports tau2.
"""

import tau2_cave  # noqa: F401  (sets TAU2_DATA_DIR before tau2 is imported)

from tau2_json_exec.agent import AGENT_NAME, Tau2JsonExecAgent, register

__all__ = ["AGENT_NAME", "Tau2JsonExecAgent", "register"]
