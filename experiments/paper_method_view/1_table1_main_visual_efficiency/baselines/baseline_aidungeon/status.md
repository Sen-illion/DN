# Status

## Current state
- status: repo cloned and runtime assessed
- owner: TBD
- last updated: 2026-04-26
- cloned commit: 591f318

## Goal
What we want from this baseline:
- provide a strong open-ended interactive narrative baseline
- compare DN against a recognizable AI story game system

## Inclusion target
Planned paper role:
- main baseline

Planned target table:
- Table 1
- optional support for Table 2 if stable long-form text outputs are available

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [ ] environment created
- [ ] baseline runnable
- [ ] smoke test passed
- [ ] benchmark subset mapped
- [ ] raw runs generated
- [ ] summary metrics generated
- [x] final decision made

## Current blockers
- upstream stack depends on `tensorflow==1.15.2`, which is a major compatibility risk on the current Windows/Python environment
- upstream local path expects GPT-2 weights downloaded through legacy scripts
- README explicitly assumes a CUDA-capable GPU and the old local generation stack is likely brittle

## Risks
- old stack may be brittle
- may require narrowing the protocol to text-only comparison
- may be more expensive to revive faithfully than to run a newer task-shape baseline

## Next action
- keep this baseline in `runtime-high-risk` state for the current paper cycle
- use `protocol/aidungeon_revival_decision_2026-04-26.md` as the go / no-go reference
- only continue in a later cycle if we explicitly reopen the legacy-runtime branch

## Final decision
- decision: no-go for the current main experiment cycle
- rationale:
  - task form matches DN very well
  - but the current public codebase is old and tied to a legacy TensorFlow/GPT-2 local runtime
  - compared with GenAgents, it is much less likely to produce paper-usable data quickly on the current machine
  - a reduced text-only rewrite would weaken its authority as a faithful baseline
  - see `protocol/aidungeon_revival_decision_2026-04-26.md`
