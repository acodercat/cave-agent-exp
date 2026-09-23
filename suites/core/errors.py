"""Framework error categories used by the evaluation and resume paths.

Mirrors the error taxonomy of a sibling harness. The distinction is load-bearing for resume:
`InfrastructureError`-shaped failures are recorded as retryable `error` turns,
while `BenchmarkSpecificationError` is a deterministic defect in benchmark
code — re-running it can never succeed, so it must fail loudly instead of
being retried forever by the resume loop.
"""


class CaveBenchError(Exception):
    """Base class for cave-bench-controlled failures."""


class InfrastructureError(CaveBenchError):
    """Retryable failure in an agent runtime, API, or network."""


class BenchmarkSpecificationError(CaveBenchError):
    """Deterministic defect in a benchmark definition, hook, or validator."""
