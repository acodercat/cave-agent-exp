#!/usr/bin/env bash
# Gemini 3.1 Pro on Airline and Retail, for R1 #7: the model that replaced the
# retired gemini-3-pro-preview, on the two domains the paper's main table covers.
#
# The protocol is the telecom campaign's, unchanged — same user simulator, same
# Gemini route and settings, same step budget, n=3 — so the two arms of a domain
# are comparable with each other and with the Telecom rows. They are NOT
# comparable with the paper's Airline/Retail rows, which ran on cave-agent 0.5.0
# against other simulators (see README, "所以这里跑出来的数字不能直接和论文…").
#
#   TAU2_API_KEY=<key> ./gemini31_domains.sh
#
# One driver per (domain, arm), side by side; each is a sweep.sh, so it resumes
# what the gateway cuts short and is restartable. DOMAINS and AGENTS narrow it.
set -uo pipefail
cd "$(dirname "$0")"
: "${TAU2_API_KEY:?the external-api-platform key}"

GATEWAY=${GATEWAY:?set GATEWAY to an OpenAI-compatible endpoint, without /v1}
MODEL=gemini-3.1-pro-preview
RUNS=${RUNS:-3}
export CONCURRENCY=${CONCURRENCY:-3}

# Copied from campaign.sh, where the simulator is defined once for the campaign:
# an arm launched without it faces run.py's defaults instead.
SIMULATOR="--user-provider openai --user-model deepseek-v4-flash-0731 --user-base-url $GATEWAY/v1 --user-thinking disabled --user-temperature 0.2"
AGENT_ARGS="--provider genai --thinking low --temperature 1.0"

mkdir -p logs
LOG=logs/campaign.log
say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

drive() {
    local domain=$1 agent=$2
    local out="logs/${domain}_${agent}_${MODEL}_n${RUNS}.log"
    say "START  $domain $agent $MODEL n=$RUNS"
    DOMAIN=$domain RUN_ARGS="$SIMULATOR $AGENT_ARGS" ./sweep.sh "$agent" "$MODEL" "$GATEWAY" "$RUNS" >>"$out" 2>&1
    local status=$?
    if [ "$status" -eq 0 ]; then say "DONE   $domain $agent $MODEL n=$RUNS"
    else say "FAILED $domain $agent $MODEL n=$RUNS (exit $status, see $out)"; fi
}

for domain in ${DOMAINS:-airline retail}; do
    for agent in ${AGENTS:-cave_agent llm_agent}; do
        drive "$domain" "$agent" &
    done
done
wait
say "GEMINI-3.1 AIRLINE/RETAIL COMPLETE"
