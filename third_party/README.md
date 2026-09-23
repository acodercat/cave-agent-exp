# third_party

`tau2.patch` is applied to Tau²-bench at commit `0ed2fd8`; the clone goes in `tau2-bench/` here
(top-level README). The patch keeps Gemini's thought signatures on tool calls across turns and
calls Anthropic models through the Anthropic API; domains, tasks and scoring are unchanged.
