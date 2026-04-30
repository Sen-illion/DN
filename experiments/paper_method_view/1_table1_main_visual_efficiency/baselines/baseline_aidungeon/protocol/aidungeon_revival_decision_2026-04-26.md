# AIDungeon Revival Decision (2026-04-26)

## Decision
- decision: `no-go for current main experiment cycle`

## Scope of this decision
This decision only concerns whether AIDungeon should be revived now as an executable baseline on the current machine for the current DN paper timeline.

It does not mean:
- AIDungeon is irrelevant
- AIDungeon is weak conceptually
- AIDungeon can never be revived later

## Why the answer is no-go now
- the public local stack is tied to `tensorflow==1.15.2`
- the expected runtime path is built around a legacy GPT-2 local generation stack
- the README and local workflow assumptions point to older CUDA-oriented setup expectations
- this makes faithful local reproduction high-risk and slow relative to the current paper needs
- GenAgents is already producing paper-usable external evidence under DN's existing `.env` API path, so the opportunity cost of switching is too high

## Can it be run faithfully on the current machine?
- answer: `not with reasonable confidence or cost right now`

Main blockers:
- legacy TensorFlow version compatibility risk on current Windows/Python environment
- legacy model download / weight management path
- likely brittle old code assumptions around local inference stack
- unclear benefit-to-effort ratio compared with the already working GenAgents path

## Is there a reduced text-only path worth trying?
- answer: `not as a priority for this paper cycle`

Why:
- a reduced path would likely stop being faithful to the original AIDungeon local stack
- once heavily reduced or rewrapped, it becomes less authoritative as a baseline
- the team already has a runnable text-side external baseline in GenAgents
- the next missing paper value is cleaner reporting and branch decisions, not another unstable integration branch

## Paper-use recommendation
Use AIDungeon as:
- a strong conceptual baseline in related work / task-form discussion
- a supplementary baseline candidate in status tables
- a deferred execution target only if a later cycle has:
  - a more compatible runtime environment
  - explicit time budget for legacy environment recovery
  - a clear need for stronger open-ended story-game task-shape comparison

## Operational consequence
- do not spend the next execution block trying to revive AIDungeon locally
- keep the status row as `runtime-high-risk`
- prioritize:
  1. freezing the current GenAgents text-baseline package
  2. optional normalized export / appendix cleanup
  3. StoryDiffusion defer note maintenance only
