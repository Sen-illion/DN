# DN Human Evaluation Protocol v1

Goal: run human evaluation with the same metrics as the LLM judges, but with stricter calibration and auditable evidence.

## Metrics

### Text coherence

Use the exact 1-5 plot-coherence scale from `DN-experiment-2.0/eval_plot_coherence.py`:

- 5: perfectly coherent; character behavior is stable, scene transitions are natural, events have clear causality, and the story has a complete main thread.
- 4: mostly coherent; minor logic defects do not affect overall understanding.
- 3: basically coherent; obvious jumps exist, but the main thread is still recoverable.
- 2: weak coherence; characters/scenes often change abruptly, logic is confused, and understanding is difficult.
- 1: incoherent; sentences/events do not connect into a story.

Strict human rule: if a sample has any unresolved contradiction about protagonist identity, objective, time order, or causal chain, it cannot receive 5.

### Image consistency

Use the exact LLM dimensions from `multiview_judgement.schema.json`:

- `semantic_consistency`: core scene intent and event match.
- `subject_attribute_consistency`: identity, count, key attributes, and object class stability.
- `spatial_consistency`: relative position, scale logic, depth, and geometry coherence.
- `style_lighting_consistency`: style unity, color temperature, direction and strength of light.
- `detail_integrity`: critical local details, artifact severity, and structural correctness.
- `overall_score`: holistic judgment aligned with the dimension scores.
- `confidence`: human confidence in [0, 1].
- `reasons`: 2-4 short evidence-based reasons.
- `failure_tags`: short labels for defects.

Use the same 1-5 anchors:

- 5: strongly consistent, no material defect.
- 4: mostly consistent, minor defect that does not change interpretation.
- 3: mixed quality, noticeable inconsistency or uncertainty.
- 2: major inconsistency, likely to affect interpretation.
- 1: severe failure, inconsistent with intent or internally broken.

Strict human rule: `overall_score` should normally be no higher than the second-lowest dimension score + 1. If any key story-critical object/person is missing or wrong, `semantic_consistency` and `overall_score` cannot exceed 3.

## Human Evaluation Design

- Use at least 2 independent raters; use 3 raters if the result will be used as a paper-quality claim.
- Blind raters to model/config names. Show only anonymized sample IDs and required context.
- Randomize sample order per rater.
- Include 5-10% duplicate samples to measure intra-rater stability.
- Include several known bad/good calibration examples before scoring starts.
- Require evidence: every non-5 score must include at least one concrete reason.
- Do not allow neutral default scoring: if evidence is insufficient, lower confidence and avoid 5.

## Disagreement And Adjudication

Flag a sample for adjudication when any of these are true:

- max-min score difference >= 2 on `overall_score`.
- max-min score difference >= 2 on any required dimension.
- one rater marks a disqualifying defect and another gives overall >= 4.
- confidence-weighted mean differs from plain mean by >= 0.35.

Adjudication should preserve original rater scores and add a separate `adjudicated_score`, not overwrite raw ratings.

## Reporting

For each metric, report:

- mean, median, standard deviation, and count.
- per-rater mean to expose strictness differences.
- disagreement rate.
- adjudication rate.
- pass rate under the selected threshold.

Recommended pass threshold: overall >= 4.0 and no disqualifying defect. For strict claims, require every dimension mean >= 4.0 as well.
