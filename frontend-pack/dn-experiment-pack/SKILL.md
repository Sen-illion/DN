---
name: dn-experiment-pack
description: "End-to-end experiment workflow for the DN project and similar research-heavy codebases. Use when Codex needs to plan, scaffold, run, compare, validate, or report experiments across model quality, consistency, efficiency, multimodal behavior, data collection, error analysis, and result documentation."
---

# DN Experiment Pack

Use this skill as the default entry point for experiment work. Pick the right specialized skill, keep the experiment reproducible, and leave behind artifacts that make comparison easy.

## Primary Goals

- turn a vague experiment idea into a concrete plan
- standardize inputs, outputs, and comparison criteria
- capture artifacts for later review
- summarize findings in a reusable format

## Core Workflow

1. Define the experiment question.
2. Identify the variable being changed and the metrics being observed.
3. Choose the right supporting skill or tool path.
4. Store outputs in stable files or notebooks when useful.
5. Compare results and call out uncertainty.
6. Produce a short conclusion plus next actions.

## Routing Rules

### Notebook-driven analysis

Use [jupyter-notebook](../jupyter-notebook/SKILL.md) when the task needs a reproducible notebook for ablations, comparisons, metric analysis, prompt studies, or exploratory result inspection.

Prefer an experiment notebook when you need to:

- compare prompt variants
- inspect generated samples and their scores
- chart latency, token use, cost, or pass rates
- document analysis that other teammates should rerun

### Repeatable experiment commands

Use [cli-creator](../cli-creator/SKILL.md) when the DN project has a recurring experiment workflow that should become a durable CLI instead of an ad hoc script.

Good fits include:

- batch evaluation runners
- sample generation commands
- JSON result exporters
- comparison commands such as `compare`, `aggregate`, or `doctor`

Prefer a CLI when the same workflow will be reused across threads or by multiple people.

### Visual artifact capture

Use [screenshot](../screenshot/SKILL.md) when experiment evidence depends on UI state, rendered images, app screens, side-by-side comparisons, or system-level captures that other tools cannot provide.

This is useful for:

- image-text consistency reviews
- visual regression checks
- generated page comparisons
- preserving examples for manual labeling

### Audio or speech experiments

Use [transcribe](../transcribe/SKILL.md) when the experiment involves spoken input, audio outputs, annotations from recordings, or converting review sessions into text for analysis.

### Report-ready documents

Use [doc](../doc/SKILL.md) when the results should be delivered as a polished document, and use [pdf](../pdf/SKILL.md) when the final artifact should be shared in a stable fixed-layout format.

Use this path for:

- experiment reports
- weekly summaries
- result packets for review
- benchmark snapshots for stakeholders

## Experiment Design Checklist

Before running or scaffolding work, define:

- hypothesis or decision question
- independent variable being changed
- fixed conditions and controls
- success metrics and failure signals
- sample size or example set
- output format for comparison

If these are missing, infer a reasonable structure and state the assumptions.

## Common DN Experiment Types

Use this skill for many experiment classes, not only one modality:

- prompt and system prompt ablations
- model-to-model comparisons
- image-text consistency checks
- style fidelity checks
- generation speed and throughput studies
- token, cost, or latency tracking
- workflow regression checks
- dataset sampling and inspection
- qualitative error bucketing
- human review packet creation

## Output Standards

Whenever practical, leave behind artifacts that can be reused:

- a notebook for analysis-heavy work
- a command or script entry point for repeated runs
- screenshots or saved samples for qualitative review
- a document or PDF for conclusions and sharing

## Final Response Checklist

Before finishing, report:

- the experiment goal
- what changed versus what stayed fixed
- where the artifacts were written
- what evidence was collected
- the strongest takeaway
- the biggest remaining uncertainty
