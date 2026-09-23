#!/bin/bash
# One arm of the Q5 pipeline study (three agents) for one model, run in chunks of
# cases with one driver process per chunk.
#
# A driver process grows by about 200 MB per pipeline it runs, so each chunk runs
# in its own process and exits. Several copies may share an arm: a copy claims a
# chunk by creating its lock directory (atomic) and skips chunks another holds.
# The resume rule skips runs already stored, so any chunk can be repeated safely.
# Clear logs/locks/<experiment>/ after a killed copy.
#
#   scripts/drivers/x3_arm.sh <model> <arm> [concurrency] [cases-per-chunk] [first-chunk] [commit]
#
# <model> is a section of models.toml; <arm> is one of cave, file, text, json.
# <commit> pins the study to the code it was begun at (default: HEAD).
cd "$(dirname "$0")/../.." || exit 1
[ -f .env ] && { set -a; . ./.env; set +a; }
model=$1; arm=$2; concurrency=${3:-3}; per_chunk=${4:-6}; first=${5:-0}
commit=${6:-$(git rev-parse HEAD)}
experiment="x3-orch-$model-$arm"
progress="logs/x3-$model.progress"
locks="logs/locks/$experiment"; mkdir -p "$locks"
mapfile -t cases < <(uv run python -c "
from cases.pipeline import PIPELINE_CASES
print('\n'.join(case.name for case in PIPELINE_CASES))")
chunks=$(( (${#cases[@]} + per_chunk - 1) / per_chunk ))
echo "$arm start@$first $(date +%m-%d\ %H:%M)" >> "$progress"
for ((step = 0; step < chunks; step++)); do
  index=$(( (first + step) % chunks )); start=$(( index * per_chunk ))
  mkdir "$locks/$index" 2>/dev/null || continue
  chunk=("${cases[@]:start:per_chunk}")
  for attempt in 1 2 3; do
    ( ulimit -t $((3 * 3600)); exec uv run python -m scripts.run_pipeline --study orchestrated \
        --model "$model" --channel "$arm" --pipeline main --experiment "$experiment" \
        --repeats 3 --concurrency "$concurrency" --protocol-nudges 0 --begun-at "$commit" \
        --case "${chunk[@]}" ) >> "logs/$experiment.log" 2>&1
    rc=$?
    echo "$arm chunk#$index attempt $attempt rc=$rc $(date +%m-%d\ %H:%M)" >> "$progress"
    [ $rc -eq 0 ] && break
  done
  rmdir "$locks/$index" 2>/dev/null
done
echo "$arm end@$first $(date +%m-%d\ %H:%M)" >> "$progress"
