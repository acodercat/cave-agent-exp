#!/usr/bin/env bash
# The telecom campaign for the TIST revision, one sweep at a time.
#
# Four agent models x two paradigms, all played against the same user
# simulator. Every combination is brought to n=3 before any is taken to n=6, so
# stopping partway leaves a complete comparison rather than an uneven one.
# Serial because every sweep leans on the simulator's gateway, which drops
# requests under parallel load.
#
#   TAU2_API_KEY=<external key> ./campaign.sh
#
# RUN_COUNTS sets the stages, "3 6" by default; RUN_COUNTS=3 stops at n=3.
# AGENTS picks the paradigms, "cave_agent llm_agent" by default; ONLY_MODEL
# limits the sweep to one model. An arm added later must be run from here and
# not from sweep.sh directly: SIMULATOR is defined once, in this file, and an
# arm launched without it takes run.py's defaults instead — which is how the
# first json_exec runs came to face a user simulator at temperature 0.0 while
# cave and llm_agent faced one at 0.2, and paired.py refused to compare them.
#
#   AGENTS=json_exec_agent ONLY_MODEL=qwen3.8-flash RUN_COUNTS=3 ./campaign.sh
#
# EXTRA_ARGS appends to every run.py invocation, for a one-off that must still
# meet the same simulator — a repeat pinned to an earlier run's seed, say:
#
#   FIRST_RUN=4 RUN_COUNTS=4 AGENTS=cave_agent ONLY_MODEL=gemini-3.1-pro-preview \
#       EXTRA_ARGS="--seed 300" ./campaign.sh
#
# Progress goes to logs/campaign.log, one line per sweep started or finished;
# each sweep's own output to logs/<agent>_<model>_n<runs>.log. Restartable:
# sweeps skip runs already complete on disk.

set -uo pipefail

cd "$(dirname "$0")"
: "${TAU2_API_KEY:?the external-api-platform key}"

GATEWAY=${GATEWAY:?set GATEWAY to an OpenAI-compatible endpoint, without /v1}
export CONCURRENCY=${CONCURRENCY:-3}
# The user simulator, held fixed for every agent. Nothing is left to a model
# default: reasoning and temperature are stated on every request.
SIMULATOR="--user-provider openai --user-model deepseek-v4-flash-0731 --user-base-url $GATEWAY/v1 --user-thinking disabled --user-temperature 0.2"

# model, its endpoint, and its settings as the agent. Gemini 3.1 Pro cannot turn
# reasoning off; it runs at its lowest level and the temperature Google requires.
MODELS=(
    "deepseek-v4-flash       $GATEWAY/v1  --api-model deepseek-v4-flash-0731 --thinking disabled --temperature 0.2"
    "qwen3.8-flash           $GATEWAY/v1  --thinking disabled --temperature 0.2"
    "deepseek/deepseek-v3.2  $GATEWAY/v1  --thinking disabled --temperature 0.2"
    "gemini-3.1-pro-preview  $GATEWAY     --provider genai --thinking low --temperature 1.0"
)

mkdir -p logs
LOG=logs/campaign.log
say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

sweep() {
    local agent=$1 model=$2 endpoint=$3 agent_args=$4 runs=$5
    local out="logs/${agent}_${model//\//-}_n${runs}.log"
    say "START  $agent $model n=$runs"
    RUN_ARGS="$SIMULATOR $agent_args ${EXTRA_ARGS:-}" ./sweep.sh "$agent" "$model" "$endpoint" "$runs" >>"$out" 2>&1
    local status=$?
    if [ "$status" -eq 0 ]; then say "DONE   $agent $model n=$runs"
    else say "FAILED $agent $model n=$runs (exit $status, see $out)"; fi
}

for runs in ${RUN_COUNTS:-3 6}; do
    for entry in "${MODELS[@]}"; do
        read -r model endpoint agent_args <<<"$entry"
        if [ -n "${ONLY_MODEL:-}" ] && [ "$model" != "$ONLY_MODEL" ]; then continue; fi
        for agent in ${AGENTS:-cave_agent llm_agent}; do
            sweep "$agent" "$model" "$endpoint" "$agent_args" "$runs"
        done
    done
done
say "CAMPAIGN COMPLETE"
