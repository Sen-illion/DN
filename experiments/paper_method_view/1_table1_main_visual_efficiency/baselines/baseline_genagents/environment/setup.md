# Environment Setup

## Goal
Record the exact installation and runtime setup for this baseline.

## Machine
- OS: Windows (current DN workspace machine)
- Python: 3.10.11 in `.venv-genagents`
- CUDA: not required for the current baseline path
- GPU: not required for the current baseline path

## Steps
1. Cloned upstream repo to:
   - `experiments/external_baselines/genagents`
2. Created dedicated environment:
   - `py -3.10 -m venv experiments/external_baselines/genagents/.venv-genagents`
3. Installed upstream dependencies from `requirements.txt`
4. Added `simulation_engine/settings.py` that reads:
   - `GENAGENTS_API_KEY` / `GENAGENTS_BASE_URL` / `GENAGENTS_MODEL`
   - and falls back to DN's `.env` provider style:
     - `Camera_Analyst_API_KEY`
     - `Camera_Analyst_BASE_URL`
     - `Camera_Analyst_MODEL`
5. Ran local smoke script:
   - `protocol/run_genagents_smoke.py`
6. Confirmed public sample agent can be loaded without error
7. Patched `gpt_structure.py` so chat and embedding calls both honor `base_url`
8. Verified live 3-turn run using DN's existing `.env` test API route

## Runtime assets
- checkpoint / model: no local checkpoint; upstream uses OpenAI API-backed models
- inference mode: API-backed text generation
- live verified provider mode: DN `.env` compatible OpenAI-style endpoint
- live verified model on 2026-04-26: `gemini-3.1-flash-lite-preview`

## Notes
- smoke artifact written to:
  - `raw_runs/genagents_smoke_2026-04-25.json`
- current smoke result:
  - sample agent `Joon Park` loaded successfully
  - sample agent memory node count: 116
  - active utterance test was skipped because no `OPENAI_API_KEY` was present in the shell environment
- a 3-turn consistency runner is now prepared and has already emitted a credential-blocked pending run:
  - `raw_runs/genagents_consistency_2026-04-25_pending.json`
- a DN-env live run has now succeeded:
  - `raw_runs/genagents_consistency_live_2026-04-26_dn_env.json`
