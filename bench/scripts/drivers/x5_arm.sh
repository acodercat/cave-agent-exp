#!/bin/bash
# One arm of the Q5 chain study for one model, in chunks, deepest chains first.
#
# A depth-8 run can take most of an hour, so chunks start with the deepest cases
# and the tail of an arm does not wait on one. Chunks are claimed by lock
# directories as in x3_arm.sh; the resume rule skips runs already stored. Every
# attempt's exit status goes to the progress file.
#
#   scripts/drivers/x5_arm.sh <model> <arm> [concurrency] [cases-per-chunk] [first-chunk] [depth] [commit]
#
# <arm> is one of cave, file, file_shared, text, json; <depth> (1, 4 or 8) limits
# the run to one depth, as for file_shared, which is run at depth 8 only.
cd "$(dirname "$0")/../.." || exit 1
[ -f .env ] && { set -a; . ./.env; set +a; }
model=$1; arm=$2; concurrency=${3:-4}; per_chunk=${4:-2}; first=${5:-0}; depth=${6:-}
commit=${7:-$(git rev-parse HEAD)}
experiment="x5-rounds-$model-$arm"
progress="logs/x5-$model.progress"
locks="logs/locks/$experiment"; mkdir -p "$locks"
mapfile -t cases < <(uv run python -c "
from cases.rounds import ROUNDS_CASES
depth = '$depth'
chosen = [c for c in ROUNDS_CASES if not depth or c.depth == int(depth)]
print('\n'.join(c.name for c in sorted(chosen, key=lambda c: -c.depth)))")
chunks=$(( (${#cases[@]} + per_chunk - 1) / per_chunk ))
echo "$arm start@$first $(date +%m-%d\ %H:%M)" >> "$progress"
for ((step = 0; step < chunks; step++)); do
  index=$(( (first + step) % chunks )); start=$(( index * per_chunk ))
  mkdir "$locks/$index" 2>/dev/null || continue
  chunk=("${cases[@]:start:per_chunk}")
  for attempt in 1 2 3; do
    ( ulimit -t $((4 * 3600)); exec uv run python -m scripts.run_pipeline --study rounds \
        --model "$model" --channel "$arm" --experiment "$experiment" --repeats 3 \
        --concurrency "$concurrency" --protocol-nudges 0 --step-budget 14 --orchestrator-step-budget 24 \
        --begun-at "$commit" --case "${chunk[@]}" ) >> "logs/$experiment.log" 2>&1
    rc=$?
    echo "$arm chunk#$index attempt $attempt rc=$rc cases=${chunk[*]} $(date +%m-%d\ %H:%M)" >> "$progress"
    [ $rc -eq 0 ] && break
  done
  rmdir "$locks/$index" 2>/dev/null
done
echo "$arm end@$first $(date +%m-%d\ %H:%M)" >> "$progress"
