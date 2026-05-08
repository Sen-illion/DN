# DOC Adapter

## Baseline nature
- text-first long-story generation baseline
- native upstream flow is premise -> outline -> long story draft
- not a native DN playable-engine baseline

## DN -> DOC mapping
- `theme` -> DOC premise seed
- `expected_genre` + `expected_tone` -> prompt style and narrative framing
- `must_have_constraints` -> outline/story guardrails
- `forbidden_issues` -> explicit failure-avoidance notes
- DN run mode -> `first_playable` or `next_turn`

## Fallback strategy
- preserve DOC semantics at a high level:
  - premise
  - outline seed
  - playable opening/story response
- do not claim upstream DOC model execution
- emit schema-compliant artifacts that DN comparison code can ingest immediately

## Real DOC dependencies
- `OPENAI_API_KEY`
- `baselines/DOC/doc_data`
- GPT3 or Alpa/OPT serving path described in upstream DOC README

## Output policy
- `baseline_id` is always `doc`
- fallback artifacts must clearly state that upstream DOC was not executed
- if real mode dependencies are missing, emit failure artifacts instead of crashing
