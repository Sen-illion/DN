---
name: frontend-pack
description: "End-to-end frontend build workflow for polished websites, landing pages, dashboards, app UIs, and prototype pages. Use when Codex needs a reusable frontend process that can design and implement a new UI, turn a Figma design into code, verify the result in a real browser, or choose between greenfield visual design and Figma-driven implementation."
---

# Frontend Pack

Use this skill as the default entry point for frontend work. Route the task to the right specialized skill, then bring the result back into one coherent implementation workflow.

## Core Workflow

1. Classify the request before writing code.
2. Choose the matching specialized skill.
3. Implement the UI using the repo's conventions.
4. Verify the result in a real browser when feasible.
5. Report what was built, what was verified, and any remaining gaps.

## Routing Rules

### Greenfield UI build

Use [frontend-skill](../frontend-skill/SKILL.md) when the user wants a new landing page, homepage, website section, app screen, dashboard, prototype, or visually strong UI without a Figma source of truth.

Before building, always define:

- visual thesis
- content plan
- interaction thesis

Then implement the page with deliberate hierarchy, restrained composition, and strong mobile behavior.

### Figma to code

Use [figma-implement-design](../figma-implement-design/SKILL.md) when the user provides a Figma link, selected Figma node, or asks to match a design precisely.

Follow its required workflow in order:

1. get the node or selection
2. fetch design context
3. capture screenshot reference
4. download assets from Figma sources
5. translate to project conventions
6. validate for visual parity

If the task also requires writing into Figma itself, load [figma-use](../figma-use/SKILL.md) before every `use_figma` call.

### Browser verification

Use [playwright](../playwright/SKILL.md) after implementation when the page can be run locally and browser validation is practical.

Default verification loop:

1. start or use the local app
2. open the target page in Playwright
3. snapshot the page state
4. test the main interaction path
5. re-snapshot after meaningful UI changes
6. capture a screenshot when visual proof is useful

Prefer headed mode when checking layout, animation, or hover behavior.

## Decision Tree

- If the request includes a Figma URL or asks for exact design fidelity, start with `figma-implement-design`.
- If the user asks for a fresh page, redesign, marketing site, or a polished UI direction, start with `frontend-skill`.
- If a real browser can be used, finish with `playwright` validation.
- If Figma canvas edits are required, invoke `figma-use` first, then perform the Figma operation incrementally.

## Build Standards

- Prefer strong typography, spacing, and composition over decorative UI clutter.
- Preserve the existing design system and code patterns when the repo already has them.
- Make desktop and mobile both feel intentional.
- Do not leave the UI unverified if browser testing is available.
- Call out any mismatch between the brief, the codebase constraints, and the final implementation.

## Deliverable Checklist

Before finishing, ensure the final response covers:

- what workflow path was chosen
- what files or screens were changed
- what browser checks were performed
- what remains unverified or needs user input
