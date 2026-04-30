# Baseline Repositories

Generated on: 2026-04-27

This registry records the new baseline repositories requested for the current experiment cycle. Existing legacy baselines under `experiments/external_baselines` are intentionally left untouched.

| Baseline | Role | Local path | Remote URL | Commit / status | Notes |
| --- | --- | --- | --- | --- | --- |
| DOC | text baseline | `baselines/DOC` | https://github.com/yangkevin2/doc-story-generation.git | 9d727cdbae40c72169ab03b729bff4419a113dac | Direct repository for DOC. Rolling is handled later as a DOC/rolling protocol configuration rather than a separate clone. |
| stable-diffusion-2-1-base / SDM-v2 | image baseline | `baselines/stable-diffusion-2-1-base/stablediffusion` | https://github.com/Stability-AI/stablediffusion.git | not cloned | Requested upstream URL currently returns Repository not found during git clone/ls-remote, so no repository was cloned. 2.1-base weights remain a later separate download task. |
| StoryDiffusion | image baseline | `baselines/StoryDiffusion` | https://github.com/HVision-NKU/StoryDiffusion.git | 8de45e424887766fdd84dc917436ff8605f00149 | Repository cloned shallowly. Dependencies, weights, and smoke runs are not installed/run in this step. |
| IC-LoRA | image baseline | `baselines/IC-LoRA` | https://github.com/ali-vilab/In-Context-LoRA.git | 966e00a826da91512fc473705bd09183f3946b21 | Repository cloned shallowly. Dependencies, weights, and smoke runs are not installed/run in this step. |

## Text Baseline Notes

- `DOC` maps to `baselines/DOC`.
- `Rolling`, `w/oIG`, and `w/oMW` do not have independent clone directories in this step; they should be represented later as experiment protocol/configuration variants.

## Image Baseline Notes

- `StoryDiffusion` maps to `baselines/StoryDiffusion`.
- `IC-LoRA` maps to `baselines/IC-LoRA`.
- `stable-diffusion-2-1-base / SDM-v2` was requested from `https://github.com/Stability-AI/stablediffusion.git`, but that URL is not cloneable at the time of setup. Keep the parent folder for this baseline and resolve the upstream code/model source before environment setup.

## Not Done In This Step

- No Python environments were created.
- No model weights or checkpoints were downloaded.
- No model smoke tests were run.
