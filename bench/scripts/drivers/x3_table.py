"""The orchestrated study's paper table: one row per arm, success and tokens.

Success is the analyst's answers against the reference. Tokens are the study's
estimated counts, summed over the orchestrator and every worker run, reported
as a median over cases and per size.

How the orchestrator directed its workers — which ran, in what order, how often,
which were skipped — is recorded in every run and released with the data, but it
is not a column here: it is diagnosis, and a reader deciding between these media
needs the outcome and its cost.

With ``--planned N`` success is passes over the N runs the arm was to make, so a
run the arm could not complete counts as a failure, as a run with no valid
delivery does in the delivery study. One case needs it: on DeepSeek the text and
json arms never completed ``bank_state_footprint_500`` (476 rows, 0.76 of the
output limit) in 18 and 10 attempts, every one ending in a provider error on the
long reply, while the cave and file arms completed it 3 of 3 through the same
gateway. Tokens are over the runs that ran: a run stored as timed out (the
guard was lowered to an hour for the last of qwen3.8-flash's text and json runs,
and a run past it is stored as failed) counts against success and has no tokens.
"""
import collections, glob, json, statistics, sys


def tokens(spent):
    return spent.get("estimated_prompt_tokens", 0) + spent.get("estimated_completion_tokens", 0)


def run_tokens(record):
    return tokens(record["orchestrator"]["spent"]) + sum(tokens(w["spent"]) for w in record["workers"])


def ran(rows):
    """The runs that ran: a run stored as timed out has no agents and no tokens."""
    return [row for row in rows if "orchestrator" in row]


def table(prefix, arms, planned=None):
    print(f"{'arm':6} {'n':>4} {'success':>8} {'tokens (median)':>16}   by size 10 / 250 / 500")
    for arm, experiment in arms:
        rows = [json.load(open(p)) for p in glob.glob(f"{prefix}-{experiment}/runs/*/*/*/pipeline.json")]
        if not rows:
            continue
        by_size = collections.defaultdict(list)
        for row in ran(rows):
            by_size[row["case"].rsplit("_", 1)[1]].append(run_tokens(row))
        size = lambda k: f"{statistics.median(by_size[k])/1000:.0f}k" if by_size.get(k) else "-"
        n = planned or len(rows)
        print(
            f"{arm:6} {n:>4} {sum(r['success'] for r in rows)/n:>8.3f}"
            f" {statistics.median(map(run_tokens, ran(rows)))/1000:>15.0f}k"
            f"   {size('10'):>5} / {size('250'):>5} / {size('500'):>5}"
        )


if __name__ == "__main__":
    arguments = sys.argv[1:]
    planned = None
    if "--planned" in arguments:
        at = arguments.index("--planned")
        planned = int(arguments[at + 1])
        del arguments[at:at + 2]
    prefix, *rest = arguments
    table(prefix, [a.split("=") for a in rest], planned)
