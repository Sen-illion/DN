# Cleanup Candidates

No files have been deleted. This file is a review checklist for a later cleanup pass.

## Safe To Delete After Confirmation

These are cache/temp/helper artifacts that are normally reproducible or not part of experiment evidence:

- `.pytest_cache`
- `.tmp_pip`
- `__pycache__`
- `_curl_test.bat`
- `_list_pkgs.py`
- `_run.bat`
- `_test_api.py`
- `DN-experiment-2.0/__pycache__`
- `DN-experiment-2.0/ablations/generation_context_ablation/__pycache__`
- `DN-experiment-2.0/ablations/protagonist_ref_ablation/scripts/__pycache__`
- `DN-experiment-2.0/human_evaluation/scripts/__pycache__`
- `DN-experiment-2.0/图片一致性_experiment/multiview_image_consistency/scripts/__pycache__`
- `experiments/baselines/doc_baseline/__pycache__`
- `experiments/baselines/re3_baseline/__pycache__`
- `experiments/doc4o_baseline/__pycache__`
- `scripts/__pycache__`
- `src/__pycache__`
- `src/characters/__pycache__`
- `src/game/__pycache__`
- `src/image/__pycache__`
- `src/llm/__pycache__`
- `src/story/__pycache__`
- `src/utils/__pycache__`
- `src/wiki/__pycache__`
- `src/worldview/__pycache__`
- `tmp_remote_check_comfy_env.sh`
- `tmp_remote_check_comfy_status.sh`
- `tmp_remote_check_hf_env.sh`
- `tmp_remote_check_running_comfyui.sh`
- `tmp_remote_comfy_help.sh`
- `tmp_remote_comfy_quick_test.sh`
- `tmp_remote_comfy_quick_test_db.sh`
- `tmp_remote_comfy_versions.sh`
- `tmp_remote_download_movie_shots.sh`
- `tmp_remote_hello.sh`
- `tmp_remote_inspect.sh`
- `tmp_remote_install_av.sh`
- `tmp_remote_install_binary_wheels.sh`
- `tmp_remote_install_comfyui.sh`
- `tmp_remote_poll_comfyui_install.sh`
- `tmp_remote_poll_pid_only.sh`
- `tmp_remote_ps_comfyui.sh`
- `tmp_remote_retry_comfy_reqs.sh`
- `tmp_remote_retry_comfy_reqs2.sh`
- `tmp_remote_show_comfy_reqs.sh`
- `tmp_remote_show_comfy_reqs_retry_log.sh`
- `tmp_remote_start_comfyui_install_bg.sh`
- `tmp_remote_stat_models.sh`
- `tmp_remote_story_versions.sh`
- `tmp_remote_tail_comfy_retry2.sh`
- `tmp_remote_validate_comfyui_env.sh`

## Archived Instead Of Deleted

Archived on 2026-05-01T12:23:29 to `experiments/_archive_or_cleanup_candidates/archive_20260501_122223`. No original files from this section remain in place unless recreated later.

- `experiments/efficiency_phase1` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__efficiency_phase1`
- `outputs/baseline_image_from_dn_text/run_20260430_144923` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/outputs__baseline_image_from_dn_text__run_20260430_144923`
- `experiments/baselines/text_doc_smoke` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__baselines__text_doc_smoke`
- `experiments/baselines/text_doc_patched_fallback4_smoke` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__baselines__text_doc_patched_fallback4_smoke`
- `experiments/baselines/text_doc_patched_fallback3` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__baselines__text_doc_patched_fallback3`
- `experiments/baselines/text_doc_patched_fallback4` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__baselines__text_doc_patched_fallback4`
- `experiments/text_ablation/archive_bad_20260425_223848` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__text_ablation__archive_bad_20260425_223848`
- `experiments/text_ablation/archive_duplicates` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/experiments__text_ablation__archive_duplicates`
- `outputs/baseline_run_summary.json` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/outputs__baseline_run_summary.json`
- `DN-experiment` -> `experiments/_archive_or_cleanup_candidates/archive_20260501_122223/DN-experiment`

## Keep

These are currently useful and were either copied into `experiments/organized` or remain primary sources:

- `experiments/organized`
- `outputs/baseline_image_from_dn_text/run_20260430_145825`
- `experiments/paper_method_view`
- `experiments/paper_modules`
- `DN-experiment-2.0/ablations`
- `DN-experiment-2.0/human_evaluation`
- `experiments/text_ablation/results`
- `experiments/baselines/image_consistency_game_themes_100`

## Missing Or Not Fully Ready

- IC-LoRA latest baseline has manifest rows but no successful generated images.
- DreamSim image metric is not completed.
- Formal human evaluation has templates/checks only, not enough samples/raters.
- Cost/resource table is still missing for paper-ready main results.

## Recommended Next Cleanup Policy

1. Review this file and decide which `Safe To Delete` items can be removed.
2. Move `Archive Instead Of Delete` items to `experiments/_archive_or_cleanup_candidates` before hard deletion.
3. Keep all raw runs that back a reported metric until final tables are frozen.