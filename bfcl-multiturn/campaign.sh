#!/usr/bin/env bash
# Both paradigms, four models, n=3.
#
# The models run in parallel, their two arms one after the other. Unlike tau2's
# campaign this benchmark has no user simulator -- each turn's user message is
# fixed text -- so a run puts half the load on the gateway, and four at four
# tasks each was probed before this was written: no request was dropped. The arms
# stay sequential within a model so its two halves cannot race for the same
# rate limit.
#
# Each run is restartable and skips tasks already scored, so stopping partway and
# starting again loses nothing.
#
#   BFCL_API_KEY=<key> ./campaign.sh          # runs 1..3
#   RUNS="2 3" ./campaign.sh                  # just those
#   SERIAL=1 ./campaign.sh                    # one model at a time, if the
#                                             # gateway starts refusing
#
# Progress goes to logs/campaign.log, each run's own output to
# logs/<arm>_<model>_run<n>.log.

set -uo pipefail
cd "$(dirname "$0")"
: "${BFCL_API_KEY:?the gateway key}"

GATEWAY=${GATEWAY:?set GATEWAY to an OpenAI-compatible endpoint, without /v1}
CONCURRENCY=${CONCURRENCY:-4}
# A task the gateway will not finish must not hold the stage open: litellm retries
# inside its own call, so one task once kept a run alive for an hour on repeated
# "Backend buffer overflow" replies, and every later run waited on it.
TASK_TIMEOUT=${TASK_TIMEOUT:-900}

# model label, then the arguments that reach the endpoint. Nothing is left to a
# provider default: reasoning and temperature are stated for every model.
#
# Two models are served under an id that is not their label, so --api-model names
# what the endpoint answers to while results keep the label. Gemini cannot turn
# reasoning off and requires temperature 1.0, and its thought signatures only
# survive its own SDK, hence the genai provider.
MODELS=(
    "qwen3.8-flash          --base-url $GATEWAY/v1 --thinking disabled --temperature 0.2"
    "deepseek-v4-flash      --base-url $GATEWAY/v1 --api-model deepseek-v4-flash-0731 --thinking disabled --temperature 0.2"
    "deepseek-v3.2          --base-url $GATEWAY/v1 --api-model deepseek/deepseek-v3.2 --thinking disabled --temperature 0.2"
    "gemini-3.1-pro-preview --base-url $GATEWAY --provider genai --thinking unset --temperature 1.0"
)

mkdir -p logs
LOG=logs/campaign.log
say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# One model's whole share of a stage: both arms, in order.
model_stage() {
    local run=$1 model=$2 args=$3
    for arm in cave fc; do
        local out="logs/${arm}_${model}_run${run}.log"
        say "START  $arm $model run$run"
        # shellcheck disable=SC2086
        uv run --frozen python run.py --arm "$arm" --model "$model" --run "$run" \
            --concurrency "$CONCURRENCY" --task-timeout "$TASK_TIMEOUT" $args >>"$out" 2>&1
        local status=$?
        if [ "$status" -eq 0 ]; then say "DONE   $arm $model run$run"
        else say "FAILED $arm $model run$run (exit $status, see $out)"; fi
    done
}

for run in ${RUNS:-1 2 3}; do
    say "STAGE  run$run: ${#MODELS[@]} model(s)${SERIAL:+, serially}"
    for entry in "${MODELS[@]}"; do
        read -r model args <<<"$entry"
        if [ -n "${SERIAL:-}" ]; then
            model_stage "$run" "$model" "$args"
        else
            model_stage "$run" "$model" "$args" &
        fi
    done
    # A stage finishes before the next begins, so stopping the campaign leaves
    # every model at the same number of runs rather than an uneven set.
    wait
    say "STAGE  run$run complete"
done
say "CAMPAIGN COMPLETE"
