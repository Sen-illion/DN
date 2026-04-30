# Environment Setup

## Goal
Record the exact installation and runtime setup for this baseline.

## Machine
- OS: Windows (current DN workspace machine)
- Python: not configured yet
- CUDA: not checked in a runnable AIDungeon environment
- GPU: upstream README recommends NVIDIA GPU with 12 GB+ VRAM for local use

## Steps
1. Clone repo
2. Assess runtime risk before environment creation
3. If still worth it, create an isolated legacy-compatible environment
4. Install dependencies and fetch GPT-2 weights
5. Run smoke test

## Runtime assets
- checkpoint / model: legacy local GPT-2 weights downloaded by upstream scripts
- inference mode: local generation
- key dependency risk: `tensorflow==1.15.2`

## Notes
- current judgment: this baseline is high-value conceptually but high-friction operationally
- defer heavy environment work until after GenAgents produces the first scored baseline run
