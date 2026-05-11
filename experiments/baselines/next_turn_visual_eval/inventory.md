# Baseline Inventory

| Baseline | Source Kind | Local Images | Candidate Pairs | Evaluable Pairs | Evaluable Now | Blocker |
| --- | --- | ---: | ---: | ---: | --- | --- |
| AIDungeon | `paper_metadata_only` | 0 | 0 | 0 | no | no_local_image_artifacts_in_paper_method_view_dir |
| DN | `dn_reference_image_manifest` | 77 | 90 | 67 | yes |  |
| DOC | `normalized_run_metadata_only` | 0 | 0 | 0 | no | normalized_run_contains_text_or_manifest_without_local_images |
| GenAgents | `paper_metadata_only+normalized_run_metadata_only` | 0 | 0 | 0 | no | no_local_image_artifacts_in_paper_method_view_dir |
| IC-LoRA | `image_sequence_index` | 100 | 90 | 90 | yes |  |
| LIGHT | `paper_metadata_only` | 0 | 0 | 0 | no | no_local_image_artifacts_in_paper_method_view_dir |
| Plan-Write-Revise | `paper_metadata_only` | 0 | 0 | 0 | no | no_local_image_artifacts_in_paper_method_view_dir |
| SDM-v2 | `image_sequence_index` | 100 | 90 | 90 | yes |  |
| StoryDiffusion | `image_sequence_index+paper_metadata_only` | 100 | 90 | 90 | yes |  |
| WorldGeneration | `paper_metadata_only` | 0 | 0 | 0 | no | no_local_image_artifacts_in_paper_method_view_dir |

## AIDungeon

- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_aidungeon`
- source_kind: `paper_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `no_local_image_artifacts_in_paper_method_view_dir`
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.

## DN

- artifact_root: `D:\DN-main\outputs\baseline_image_from_dn_text\run_20260430_145825\manifest\manifest.jsonl`
- source_kind: `dn_reference_image_manifest`
- local_image_records: `77`
- candidate_next_turn_pairs: `90`
- evaluable_pairs: `67`
- evaluable_now: `True`
- note: Pairs are built as adjacent DN reference segment images within the same game (seg_n -> seg_n+1).
- note: This uses the same local-only next-turn DINOv2 protocol as the image baselines.

## DOC

- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\formal20_first_playable_20260430`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\formal20_first_playable_20260430_complete`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\formal8_first_playable_20260430`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\formal8_first_playable_20260430_v2`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\retry_DNQBV1_008_20260430`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\doc_yunwu\smoke1_20260430`
- source_kind: `normalized_run_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `normalized_run_contains_text_or_manifest_without_local_images`
- note: Normalized run metadata exists, but no local image artifacts were found for visual evaluation.

## GenAgents

- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\genagents_consistency_live_2026-04-26_dn_env_subset_v2.normalized.json`
- artifact_root: `D:\DN-main\experiments\baseline_integration\normalized_runs\genagents_smoke_2026-04-25.normalized.json`
- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_genagents`
- source_kind: `paper_metadata_only+normalized_run_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `no_local_image_artifacts_in_paper_method_view_dir`
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.
- note: Normalized run metadata exists, but no local image artifacts were found for visual evaluation.

## IC-LoRA

- artifact_root: `D:\DN-main\outputs\baseline_image_from_dn_text\run_20260430_145825\IC-LoRA\index.jsonl`
- source_kind: `image_sequence_index`
- local_image_records: `100`
- candidate_next_turn_pairs: `90`
- evaluable_pairs: `90`
- evaluable_now: `True`
- note: Pairs are built as adjacent segments within the same game (seg_n -> seg_n+1).

## LIGHT

- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_light`
- source_kind: `paper_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `no_local_image_artifacts_in_paper_method_view_dir`
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.

## Plan-Write-Revise

- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_plan_write_revise`
- source_kind: `paper_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `no_local_image_artifacts_in_paper_method_view_dir`
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.

## SDM-v2

- artifact_root: `D:\DN-main\outputs\baseline_image_from_dn_text\run_20260430_145825\SDM-v2\index.jsonl`
- source_kind: `image_sequence_index`
- local_image_records: `100`
- candidate_next_turn_pairs: `90`
- evaluable_pairs: `90`
- evaluable_now: `True`
- note: Pairs are built as adjacent segments within the same game (seg_n -> seg_n+1).

## StoryDiffusion

- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_storydiffusion`
- artifact_root: `D:\DN-main\outputs\baseline_image_from_dn_text\run_20260430_145825\StoryDiffusion\index.jsonl`
- source_kind: `image_sequence_index+paper_metadata_only`
- local_image_records: `100`
- candidate_next_turn_pairs: `90`
- evaluable_pairs: `90`
- evaluable_now: `True`
- note: Pairs are built as adjacent segments within the same game (seg_n -> seg_n+1).
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.

## WorldGeneration

- artifact_root: `D:\DN-main\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_worldgeneration`
- source_kind: `paper_metadata_only`
- local_image_records: `0`
- candidate_next_turn_pairs: `0`
- evaluable_pairs: `0`
- evaluable_now: `False`
- blocker: `no_local_image_artifacts_in_paper_method_view_dir`
- note: Protocol/raw_run/summaries exist, but no local images were found in the workspace.
