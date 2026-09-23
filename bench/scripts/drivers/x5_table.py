"""The rounds study's tables: what survives a chain, hop by hop and by depth.

The first table is one row per arm and depth: how often the producer built the
right object (``built``), how often every crossing of the chain was clean
(``carried``), how often every stage's object was the one the chain should have
held (``applied``), the end-to-end verdict (``final``) and the host's question
(``answered``); then the chain's own failures — a stage that worked from an
earlier version (``stale``), a crossing the host could not observe because the agent bound its
input only after editing it (``unobs``, which only the arms without a runtime
slot can have — where there is one the host reads the object before the worker
runs), a stage that never ran (``skipped``), one that ran twice (``repeat``), and
how often the chain ran in its designed order at all (``order``; a hop judged
after the orchestrator went back to an earlier worker is read against the wrong
predecessor, and its record names the worker that actually ran before it) —
and what the run cost. Rates are over the runs an arm was
to make, so a chain that stopped early counts against it rather than vanishing.

The second table is the one to read for the study's question: at the deepest
chain, how often each hop's object was still right, hop by hop. A medium that
loses nothing is flat; one that loses a little at every crossing slopes.

The third says how the object was moved: files written and read, and the
characters of object payload that passed through the model — the instruction an
orchestrator wrote it into and the reply a worker wrote it into. It is a cost
column, not a verdict: the objects here are a few kilobytes, so the disk traffic
costs nothing, while the payload through the model is both paid for in tokens
and the place where a value can be rewritten.
"""
import collections, glob, json, os, re, statistics, sys


def load(prefix, experiment):
    rows = []
    for path in glob.glob(f"{prefix}-{experiment}/runs/*/*/*/pipeline.json"):
        row = json.load(open(path))
        row["_path"] = path
        rows.append(row)
    return rows


def rows_by_depth(rows):
    by_depth = collections.defaultdict(list)
    for row in rows:
        by_depth[row.get("depth", 1)].append(row)
    return by_depth


def rate(rows, predicate, planned=None):
    return sum(bool(predicate(row)) for row in rows) / (planned or len(rows) or 1)


def by_arm(prefix, arms, planned=None):
    print(
        f"{'arm':12} {'depth':>5} {'n':>4} {'built':>6} {'carried':>7} {'applied':>7} {'final':>6} "
        f"{'answered':>8} {'stale':>6} {'unobs':>6} {'skipped':>7} {'repeat':>6} {'order':>6} {'budget':>6} {'tokens':>7} {'wall':>6}"
    )
    for arm, experiment in arms:
        for depth, rows in sorted(rows_by_depth(load(prefix, experiment)).items()):
            if not rows:
                continue
            hops = lambda row: row.get("hops", [])[1:]          # the producer crosses nothing
            print(
                f"{arm:12} {depth:>5} {len(rows):>4}"
                f" {rate(rows, lambda r: r['hops'][0]['applied'], planned):>6.2f}"
                f" {rate(rows, lambda r: all(h['carried'] for h in hops(r)), planned):>7.2f}"
                f" {rate(rows, lambda r: all(h['applied'] for h in r['hops']), planned):>7.2f}"
                f" {rate(rows, lambda r: r['success'], planned):>6.2f}"
                f" {rate(rows, lambda r: r['workers'][-1].get('answered'), planned):>8.2f}"
                f" {rate(rows, lambda r: any(h.get('edited_from') is not None or h.get('matches_output_of') is not None for h in r['hops']), planned):>6.2f}"
                f" {rate(rows, lambda r: any(h.get('observed_late') for h in r['hops']), planned):>6.2f}"
                f" {rate(rows, lambda r: r['skipped'], planned):>7.2f}"
                f" {rate(rows, lambda r: r['repeated'], planned):>6.2f}"
                f" {rate(rows, lambda r: r['ran_as_designed'], planned):>6.2f}"
                f" {rate(rows, lambda r: r['budget_exceeded'], planned):>6.2f}"
                f" {statistics.median(r['tokens'] for r in rows) / 1000:>6.0f}k"
                f" {statistics.median(r['elapsed_s'] for r in rows) / 60:>5.0f}m"
            )


def by_hop(prefix, arms, depth):
    print(f"\nthe object still right at each hop, depth {depth}\n")
    print(f"{'arm':12} " + " ".join(f"{k:>5}" for k in range(depth + 1)))
    for arm, experiment in arms:
        rows = rows_by_depth(load(prefix, experiment)).get(depth, [])
        if not rows:
            continue
        cells = []
        for hop in range(depth + 1):
            seen = [row["hops"][hop]["applied"] for row in rows if len(row["hops"]) > hop]
            cells.append(f"{sum(bool(v) for v in seen) / len(rows):>5.2f}" if seen else f"{'-':>5}")
        print(f"{arm:12} " + " ".join(cells))


def by_case(prefix, arms):
    print("\nfinal verdict by object and depth\n")
    names = [a for a, _ in arms]
    runs = {arm: collections.defaultdict(list) for arm, _ in arms}
    for arm, experiment in arms:
        for row in load(prefix, experiment):
            runs[arm][row["case"]].append(row)
    every = sorted({case for arm in runs for case in runs[arm]})
    print(f"{'case':30} " + " ".join(f"{a:>11}" for a in names))
    for case in every:
        cells = []
        for arm in names:
            rows = runs[arm].get(case, [])
            cells.append(f"{sum(r['success'] for r in rows)}/{len(rows)}" if rows else "-")
        print(f"{case:30} " + " ".join(f"{c:>11}" for c in cells))


# How a worker's code moves an object, counted from its own transcript: the
# calls that write or read a file, and the characters of object payload that
# passed through the model — what the orchestrator wrote into an instruction and
# what a worker wrote into its reply. The arm that hands a reference moves the
# object through neither.
_WRITES = re.compile(r"\.to_parquet\(|joblib\.dump\(|np\.save\(")
_READS = re.compile(r"read_parquet\(|joblib\.load\(|np\.load\(")


def _messages(path):
    out = []
    for line in open(path):
        try:
            out.append(json.loads(line))
        except Exception:                           # noqa: BLE001 - a truncated transcript
            pass
    return out


def _moved(row, directory):
    """One run's handoff I/O: files written, files read, payload characters through the model."""
    writes = reads = payload = 0
    for worker in row["workers"]:
        messages = _messages(f"{directory}/{worker['transcript']}")
        code = "\n".join(
            str(m["content"]) for m in messages
            if "```" in str(m["content"]) and not str(m["role"]).lower().endswith("user")
        )
        if worker["name"] != "consumer":
            writes += len(_WRITES.findall(code))
        if worker["name"] != "producer":
            reads += len(_READS.findall(code))
        for m in messages:
            role, content = str(m["role"]).lower(), str(m["content"])
            # The instruction the orchestrator wrote, less the host's own contract.
            if role.endswith("user") and "Required outputs" in content:
                payload += content.find("Required outputs")
            elif role.endswith("assistant") and "```json" in content:
                payload += len(content)
    return writes, reads, payload


def by_io(prefix, arms):
    print("\nhow the object was moved, per run (median)\n")
    print(f"{'arm':12} {'depth':>5} {'files written':>13} {'files read':>10} {'payload through the model':>26}")
    for arm, experiment in arms:
        for depth, rows in sorted(rows_by_depth(load(prefix, experiment)).items()):
            moved = [_moved(row, os.path.dirname(row["_path"])) for row in rows]
            if not moved:
                continue
            w, r, p = (statistics.median(x[i] for x in moved) for i in range(3))
            print(f"{arm:12} {depth:>5} {w:>13.0f} {r:>10.0f} {p / 4000:>23.0f}k tok")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    planned = None
    if "--planned" in arguments:
        at = arguments.index("--planned")
        planned = int(arguments[at + 1])
        del arguments[at:at + 2]
    prefix, *rest = arguments
    arms = [a.split("=") for a in rest]
    by_arm(prefix, arms, planned)
    by_hop(prefix, arms, 8)
    by_io(prefix, arms)
    by_case(prefix, arms)
