# Image Consistency Baseline vs DN Comparison

## Input/output check
- DINOv2: input image pair(s); output JSONL rows with `dinov2_cosine` where higher means more similar.
- CLIP-I: input image pair(s); output JSONL rows with `clip_i_cosine` where higher means more similar.
- DreamSim: input image pair(s); output JSONL rows with `dreamsim_distance` where lower means more similar; default checkpoint download did not finish in this run.
- `game_themes_100.json` cannot be fed directly because it has theme/style metadata but no image paths. I converted the available DN benchmark subset into `pairs.csv`.

## Dataset
- Source theme file: `C:\Users\User\Desktop\DN-main\game_themes_100.json` (100 themes).
- DN mapped run: `C:\Users\User\Desktop\DN-main\experiments\benchmark\standard_runs\benchmark_v1_fullchain_default_20.json` (20 themes).
- Scored image pairs: 19; skipped missing scene image: 1 (`DNQBV1_008`, theme_id 27).
- Pair definition: DN `main_character.png` vs DN `scene_00001.png` for the same `game_id`.

## Score summary
- clip_i: n=19, mean=0.560501, median=0.540228, min=0.365214, max=0.75504.
- dinov2: n=19, mean=0.177302, median=0.172925, min=0.000641, max=0.450216.

## Top combined similarity
- DNQBV1_011 / theme 21 / 书院禁书风波: combined_z=2.2772, CLIP-I=0.7478, DINOv2=0.4502.
- DNQBV1_017 / theme 24 / 近地轨道维修工: combined_z=1.5562, CLIP-I=0.7550, DINOv2=0.2870.
- DNQBV1_020 / theme 18 / 沙漠商队星图: combined_z=0.9546, CLIP-I=0.6349, DINOv2=0.2965.
- DNQBV1_003 / theme 19 / 都市天台养鸽人: combined_z=0.5055, CLIP-I=0.5693, DINOv2=0.2758.
- DNQBV1_014 / theme 23 / 雨林部落预言: combined_z=0.3574, CLIP-I=0.6277, DINOv2=0.1765.

## Bottom combined similarity
- DNQBV1_015 / theme 5 / 魔法学院期末周: combined_z=-0.6156, CLIP-I=0.5289, DINOv2=0.0816.
- DNQBV1_007 / theme 20 / 意识上传遗嘱: combined_z=-0.7979, CLIP-I=0.4666, DINOv2=0.1143.
- DNQBV1_005 / theme 2 / 月球矿难七日: combined_z=-0.8174, CLIP-I=0.4705, DINOv2=0.1056.
- DNQBV1_009 / theme 3 / 茶肆说书人: combined_z=-1.3448, CLIP-I=0.4414, DINOv2=0.0259.
- DNQBV1_001 / theme 1 / 边陲驿站夜谈录: combined_z=-1.872, CLIP-I=0.3652, DINOv2=0.0006.

## Artifacts
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\pairs.csv`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\pairs_with_metadata.csv`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\clip_i_scores.jsonl`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\dinov2_scores.jsonl`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\baseline_scores_long.csv`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\baseline_vs_dn_comparison.csv`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\comparison_summary.json`
- `C:\Users\User\Desktop\DN-main\experiments\baselines\image_consistency_game_themes_100\skipped_missing_images.json`
