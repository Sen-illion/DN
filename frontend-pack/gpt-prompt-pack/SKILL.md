---
name: gpt-prompt-pack
description: "Rewrite rough user wording into clearer GPT-ready instructions. Use when Codex needs to turn a vague idea, chatty request, scattered notes, meeting text, or incomplete requirement into a structured prompt with explicit goals, inputs, constraints, and output format."
---

# GPT Prompt Pack

Use this skill as the default entry point when the user's wording is natural, incomplete, messy, or too implicit for reliable model execution. Convert it into a clearer instruction before solving the task or handing it to another model.

## Primary Goals

- preserve the user's real intent
- remove ambiguity that would confuse GPT
- surface missing assumptions
- make output expectations explicit
- choose a prompt shape that matches the task

## Core Workflow

1. Read the original wording and identify the actual job.
2. Extract what is already clear: goal, input, constraints, tone, output.
3. Identify what is missing or ambiguous.
4. Infer safe defaults when possible and state them.
5. Rewrite into a structured GPT-friendly instruction.
6. If useful, provide both a concise version and a more robust version.

## Routing Rules

### Official prompt upgrade guidance

Use [openai-docs](../openai-docs/SKILL.md) when the task depends on current OpenAI guidance, latest prompt patterns, or model-specific instruction style. Prefer this path when the user explicitly mentions GPT, OpenAI APIs, prompt optimization, or wants the prompt to better fit current OpenAI models.

### Turn vague requirements into an executable spec

Use [notion-spec-to-implementation](../notion-spec-to-implementation/SKILL.md) when the user's wording is really a product, feature, workflow, or implementation request that should be turned into a structured specification before prompt rewriting.

### Capture ideas from messy notes or conversation

Use [notion-knowledge-capture](../notion-knowledge-capture/SKILL.md) when the source material is a loose conversation, brainstorming notes, meeting text, or fragmented thoughts that first need extraction and organization.

### Synthesize multiple materials into a usable brief

Use [notion-research-documentation](../notion-research-documentation/SKILL.md) when several sources need to be combined into one coherent brief, context packet, or research summary before converting that material into model instructions.

## Rewrite Patterns

Choose the lightest useful format.

### Pattern 1: Direct instruction rewrite

Use when the user already knows the task and mostly needs cleaner phrasing.

Preferred structure:

- task goal
- required action
- constraints
- output format

### Pattern 2: Structured execution prompt

Use when the task needs dependable model behavior.

Preferred structure:

- role or context
- task goal
- provided input
- rules and constraints
- output format
- optional example

### Pattern 3: Spec-first rewrite

Use when the original wording is too vague to execute safely.

Preferred structure:

- objective
- background
- assumptions
- acceptance criteria
- final GPT instruction

## Default Clarifications To Infer

If the user does not specify them, infer and expose the most important missing pieces:

- what success looks like
- what must not change
- desired tone or style
- whether the output should be short, detailed, bullet-based, tabular, or JSON
- whether examples are needed

Do not invent domain facts. Only infer structural defaults that make the prompt more executable.

## Output Standards

When rewriting, prefer one of these deliverables:

- `Refined prompt:` a polished prompt ready to paste into GPT
- `Structured brief:` a clarified version of the request for later prompting
- `Prompt options:` two or three variants for different levels of control

When helpful, include two versions:

- a compact prompt for quick use
- a robust prompt for higher reliability

## Final Response Checklist

Before finishing, ensure the response makes clear:

- the original intent you preserved
- the assumptions you added
- the rewritten GPT-ready instruction
- any remaining ambiguity the user may want to refine later
