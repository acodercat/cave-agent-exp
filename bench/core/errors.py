"""The two failure classes that decide whether work is worth retrying.

A benchmark run fails for exactly two reasons, and they call for opposite
responses. A provider outage, a dropped connection or a runtime that died is
transient: the case is unchanged and the next attempt may succeed, so the runner
records the failure and re-queues it. A missing module, an unknown validator or a
validator that raises is deterministic: every retry burns another paid model call
on a defect that will fail identically, so the run stops and says so.

Catching both as one class makes the second look like the first.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping


class FinBenchError(Exception):
    """Base class for benchmark failures FinBench classifies deliberately."""


class InfrastructureError(FinBenchError):
    """Transient: provider, network, runtime. Retryable and resumable.

    ``spent`` is what the failed attempt had already cost before it failed, so a
    study can count every attempt it paid for, not only the one that finished.
    """

    def __init__(self, message: str, *, spent: Mapping[str, int] | None = None):
        super().__init__(message)
        self.spent: Counter[str] = Counter(spent or {})


class BenchmarkSpecificationError(FinBenchError):
    """Deterministic defect in a case, its module or its validator. Never retried."""
