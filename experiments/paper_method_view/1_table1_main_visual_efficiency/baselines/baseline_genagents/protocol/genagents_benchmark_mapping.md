# GenAgents Benchmark Mapping

## Mapping principle
GenAgents is not a full game server and does not natively produce:
- worldview JSON
- branching options
- scene images

So the DN benchmark must be adapted into a smaller comparable task:
- persona-conditioned response generation
- memory-aware multi-turn consistency
- long-range state stability

## DN to GenAgents field mapping
- `theme` -> interview stimulus / scenario prompt
- `expected_genre` -> framing hint for tone and setting
- `expected_tone` -> response style control
- `must_have_constraints` -> rubric checks for usable response
- `forbidden_issues` -> failure tags during manual or automatic review

## Normalized output unit
One GenAgents run should export:
- `benchmark_id`
- `baseline_id`
- `agent_id`
- `agent_profile`
- `prompt_bundle`
- `turn_outputs`
- `latency_s`
- `success`
- `failure_reason`
- `notes`

## Planned comparable metrics
Stronger metrics for this baseline:
- persona consistency
- setting adherence
- response usefulness
- multi-turn coherence
- invalid output rate

Weaker or unsupported metrics:
- image quality
- image-text alignment
- end-to-end interactive game latency
- branching option diversity in DN's exact format

## Recommended use in paper
- main baseline for Table 2 text-planning / state-consistency support
- partial baseline for Table 1 textual usefulness / reliability support
- not a substitute for DN's full multimodal interactive loop
