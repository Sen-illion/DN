# GenAgents Judge Protocol

## Purpose
Replace the earlier keyword-hit placeholder with a stronger paper-facing rubric for the current runnable external baseline.

## Input unit
Each judged unit is one full 3-turn GenAgents run containing:
- benchmark metadata
- theme / genre / tone target
- must-have constraints
- forbidden issues
- full prompt-response bundle
- blocked-turn markers if any

## Judge dimensions
- `theme_alignment_1to5`
- `setting_adherence_1to5`
- `persona_consistency_1to5`
- `multi_turn_coherence_1to5`
- `actionability_1to5`
- `major_error_0or1`

## Rubric intent
- `theme_alignment_1to5`: stays inside the intended story world, genre pressure, and tone
- `setting_adherence_1to5`: reflects must-have constraints and avoids forbidden derailment
- `persona_consistency_1to5`: preserves the same narrator identity and behavioral stance across turns
- `multi_turn_coherence_1to5`: later turns continue earlier turns logically without reset or contradiction
- `actionability_1to5`: gives concrete usable decisions, priorities, or next actions
- `major_error_0or1`: marks blocked turns, severe derailment, or broken output

## Current implementation
- script: `protocol/judge_genagents_runs.py`
- provider: DN `.env` OpenAI-compatible settings
- output:
  - `summaries/genagents_consistency_judged_*.json`
  - `summaries/genagents_consistency_judged_*.csv`

## Interpretation note
These judge scores are stronger than the earlier heuristic placeholders, but they are still model-based evaluation rather than human gold labels. They are suitable for current main-experiment comparison support and should be labeled accordingly in the paper draft.
