# DN Text-to-Image Baseline Comparison

- Run directory: `outputs/baseline_image_from_dn_text/run_20260430_145825`
- Vision evaluator: `gpt-4o` via `https://yunwu.ai/v1`
- Baseline generation used text prompts only. DN images were referenced only during evaluation.

## Generation Coverage

| Baseline | Successful images | Indexed rows |
| --- | ---: | ---: |
| IC-LoRA | 100 | 100 |
| SDM-v2 | 100 | 100 |
| StoryDiffusion | 100 | 100 |

## Average Scores

| Baseline | Eval pairs | DN avg | Baseline avg | Delta |
| --- | ---: | ---: | ---: | ---: |
| IC-LoRA | 77 | 4.7048 | 3.8281 | -0.8766 |
| SDM-v2 | 77 | 4.7095 | 2.4442 | -2.2654 |
| StoryDiffusion | 77 | 4.7015 | 3.6288 | -1.0727 |

## Theme Scores

| Baseline | Theme | Eval pairs | DN avg | Baseline avg | Delta |
| --- | --- | ---: | ---: | ---: | ---: |
| IC-LoRA | theme_001_game_1776417898_zthbu3 | 10 | 4.77 | 3.7483 | -1.0217 |
| IC-LoRA | theme_002_game_1776418186_406ktb | 4 | 4.6708 | 3.8708 | -0.8 |
| IC-LoRA | theme_003_game_1776418475_uho8y4 | 10 | 4.72 | 3.8083 | -0.9117 |
| IC-LoRA | theme_004_game_1776418746_kox2ae | 10 | 4.6717 | 3.8067 | -0.865 |
| IC-LoRA | theme_005_game_1776419026_gflx4b | 10 | 4.6517 | 3.8333 | -0.8184 |
| IC-LoRA | theme_006_game_1776419299_05783f | 1 | 4.8167 | 4.1667 | -0.65 |
| IC-LoRA | theme_012_game_1776419613_9xv3kl | 10 | 4.7333 | 3.835 | -0.8983 |
| IC-LoRA | theme_018_game_1776419881_ts9erz | 10 | 4.69 | 3.8334 | -0.8566 |
| IC-LoRA | theme_054_game_1776420257_ds08b3 | 2 | 4.7834 | 3.8917 | -0.8916 |
| IC-LoRA | theme_073_game_1776420517_nejnnv | 10 | 4.6833 | 3.8683 | -0.815 |
| SDM-v2 | theme_001_game_1776417898_zthbu3 | 10 | 4.7767 | 2.185 | -2.5917 |
| SDM-v2 | theme_002_game_1776418186_406ktb | 4 | 4.7166 | 3.0292 | -1.6875 |
| SDM-v2 | theme_003_game_1776418475_uho8y4 | 10 | 4.6883 | 2.3 | -2.3883 |
| SDM-v2 | theme_004_game_1776418746_kox2ae | 10 | 4.59 | 3.0533 | -1.5367 |
| SDM-v2 | theme_005_game_1776419026_gflx4b | 10 | 4.7984 | 1.9033 | -2.895 |
| SDM-v2 | theme_006_game_1776419299_05783f | 1 | 4.75 | 2.3667 | -2.3833 |
| SDM-v2 | theme_012_game_1776419613_9xv3kl | 10 | 4.7417 | 2.9183 | -1.8234 |
| SDM-v2 | theme_018_game_1776419881_ts9erz | 10 | 4.6783 | 2.6417 | -2.0367 |
| SDM-v2 | theme_054_game_1776420257_ds08b3 | 2 | 4.7083 | 1.9166 | -2.7917 |
| SDM-v2 | theme_073_game_1776420517_nejnnv | 10 | 4.6867 | 1.9867 | -2.7 |
| StoryDiffusion | theme_001_game_1776417898_zthbu3 | 10 | 4.76 | 3.6283 | -1.1317 |
| StoryDiffusion | theme_002_game_1776418186_406ktb | 4 | 4.6625 | 3.4583 | -1.2041 |
| StoryDiffusion | theme_003_game_1776418475_uho8y4 | 10 | 4.6883 | 3.5917 | -1.0967 |
| StoryDiffusion | theme_004_game_1776418746_kox2ae | 10 | 4.675 | 3.9767 | -0.6983 |
| StoryDiffusion | theme_005_game_1776419026_gflx4b | 10 | 4.6767 | 3.3583 | -1.3183 |
| StoryDiffusion | theme_006_game_1776419299_05783f | 1 | 4.75 | 4.1167 | -0.6333 |
| StoryDiffusion | theme_012_game_1776419613_9xv3kl | 10 | 4.7083 | 3.475 | -1.2333 |
| StoryDiffusion | theme_018_game_1776419881_ts9erz | 10 | 4.7283 | 3.6634 | -1.065 |
| StoryDiffusion | theme_054_game_1776420257_ds08b3 | 2 | 4.75 | 3.6167 | -1.1333 |
| StoryDiffusion | theme_073_game_1776420517_nejnnv | 10 | 4.675 | 3.73 | -0.945 |

## Failures / Skips

- Evaluation/generation skip rows: 69
- Common skip reasons include missing DN reference images or baselines that only prepared manifests.

Detailed files:

- `reports/generation_dataset_index.jsonl`
- `reports/llm_pairwise_scores.jsonl`
- `reports/llm_pairwise_scores.csv`
- `reports/summary_by_baseline.csv`
- `reports/summary_by_theme.csv`
- `reports/evaluation_failures.jsonl`
