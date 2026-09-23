#!/usr/bin/env bash
# Run one agent over a domain n times, resuming whatever the gateway cuts short.
#
# A 114-task sweep loses tasks to connection errors often enough that doing n=3
# by hand means babysitting six runs. Each run here is retried with --resume
# until its file holds the whole split, then the pieces are merged into it.
#
#   TAU2_API_KEY=... ./sweep.sh cave_agent qwen3.8-flash https://host/v1 3
#
# Arguments: agent, model, base url, number of runs (default 3).
# Everything else — domain, split, step budget — follows run.py's defaults, and
# RUN_ARGS passes anything extra through, e.g. the user simulator when it lives
# on another gateway:
#
#   RUN_ARGS="--user-model deepseek-v4-flash --user-base-url https://other/v1"
#
# DOMAIN picks the tau2 domain (default telecom). It names the files a run is
# looked up by, its lock, and the split its missing tasks are counted against, so
# one model can be swept over several domains without the sweeps meeting.
#
# FIRST_RUN starts later than run 1, so separate runs of one model can go side
# by side: FIRST_RUN=3 ./sweep.sh cave_agent qwen3.8-flash https://host/v1 3

set -euo pipefail

AGENT=${1:?agent (cave_agent or llm_agent)}
MODEL=${2:?model id}
BASE_URL=${3:?base url}
RUNS=${4:-3}
FIRST_RUN=${FIRST_RUN:-1}
DOMAIN=${DOMAIN:-telecom}
CONCURRENCY=${CONCURRENCY:-4}
MAX_ATTEMPTS=${MAX_ATTEMPTS:-6}
RETRY_PAUSE=${RETRY_PAUSE:-120}   # seconds, multiplied by the attempt number

cd "$(dirname "$0")"
: "${TAU2_API_KEY:?set TAU2_API_KEY}"

# run.py writes the model into the filename with its vendor prefix flattened.
MODEL_SLUG=${MODEL//\//-}

# Empty or no match must yield an empty string, not kill the script: `ls` fails
# when nothing matches and `pipefail` would make the pipeline fail with it.
latest() { ls -t results/*"${1}"*.json 2>/dev/null | head -1 || true; }

# One driver per run. Two drivers on the same run would both write and merge its
# file, so a driver that reaches a run another one holds waits for it, then
# finds the run complete or picks up what is left. Opening fd 9 again for the
# next run releases the previous lock.
hold_run() {
    exec 9> "/tmp/tau2-revision-${DOMAIN}-${AGENT}-${MODEL_SLUG}-run${1}.lock"
    flock -n 9 || { echo "   run ${1} is being driven elsewhere; waiting"; flock 9; }
}

# Only this run's files. tau2 rewrites a results file for every task it
# finishes, so touching another driver's file mid-write could truncate it.
redact_run() { .venv/bin/python redact.py results/*"_${DOMAIN}_${AGENT}_${MODEL_SLUG}_run${1}.json" 2>/dev/null || true; }

for run in $(seq "$FIRST_RUN" "$RUNS"); do
    echo "=== ${DOMAIN} ${AGENT} ${MODEL} run ${run}/${RUNS}"
    hold_run "$run"
    # A killed run.py cannot scrub its own file; clear anything an earlier kill left.
    redact_run "$run"

    # Restartable: a run already on disk is continued rather than started over,
    # so re-invoking this after a crash costs only the tasks still missing.
    sweep=$(latest "_${DOMAIN}_${AGENT}_${MODEL_SLUG}_run${run}")
    if [ -z "$sweep" ]; then
        .venv/bin/python run.py --domain "$DOMAIN" --agent "$AGENT" --model "$MODEL" --base-url "$BASE_URL" \
            --run "$run" --concurrency "$CONCURRENCY" ${RUN_ARGS:-} \
            || echo "   run ${run} ended early"
        sweep=$(latest "_${DOMAIN}_${AGENT}_${MODEL_SLUG}_run${run}")
    else
        echo "   continuing $(basename "$sweep")"
    fi

    [ -n "$sweep" ] || { echo "   run ${run} wrote no results file"; exit 1; }

    # Pick up whatever is missing; the sweep file is the loop's state. The pause
    # before each attempt lets a gateway outage pass instead of spending every
    # attempt inside it.
    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
        remaining=$(.venv/bin/python missing.py --domain "$DOMAIN" "$sweep" | wc -l)
        [ "$remaining" -eq 0 ] && break
        echo "   attempt ${attempt}: ${remaining} task(s) left"
        sleep $(( attempt * RETRY_PAUSE ))
        .venv/bin/python run.py --domain "$DOMAIN" --agent "$AGENT" --model "$MODEL" --base-url "$BASE_URL" \
            --run "$run" --concurrency "$CONCURRENCY" ${RUN_ARGS:-} --resume "$sweep" || true
        patch=$(latest "_${DOMAIN}_${AGENT}_${MODEL_SLUG}_run${run}")
        redact_run "$run"
        [ "$patch" = "$sweep" ] && break
        .venv/bin/python merge.py --allow-commit-change "$sweep" "$patch" \
            && mv "$patch" results/superseded/
    done
    redact_run "$run"

    # Later runs would meet whatever stopped this one; fail so the caller knows.
    remaining=$(.venv/bin/python missing.py --domain "$DOMAIN" "$sweep" | wc -l)
    if [ "$remaining" -gt 0 ]; then
        echo "   run ${run} incomplete after ${MAX_ATTEMPTS} attempts: ${remaining} task(s) left"
        exit 1
    fi
    echo "   run ${run} done: $(basename "$sweep")"
done
