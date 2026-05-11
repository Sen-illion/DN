# Hard Identity Protagonist Reference Ablation - Curated Standard Results

Source dataset: `protagonist_ref_hard_identity_dataset_20260426_033440`

Source run: `protagonist_ref_hard_identity_run_20260426_040417`

## Curation rule

???????????? `base_game_id` ???? 0/1/3 ????????? `actual_protagonist_ref_count == expected_protagonist_ref_count`?

???game_1777174480_6ia5jp

???game_1777175018_804e9w, game_1777175534_kzyqsf

## Retained data

- Strict scenes: 10
- Strict group samples: 30
- Groups: protagonist_ref_0 / protagonist_ref_1 / protagonist_ref_3

## Main summary

| Group | N | Actual refs | Overall | Identity Fidelity | View Match | Detail |
|---|---:|---|---:|---:|---:|---:|
| `protagonist_ref_0` | 10 | [0] | 8.8 | 9.1 | 8.7 | 8.5 |
| `protagonist_ref_1` | 10 | [1] | 8.8 | 9.1 | 8.6 | 8.7 |
| `protagonist_ref_3` | 10 | [3] | 9.0 | 9.1 | 9.0 | 8.9 |

## Conservative conclusion

?????? 10 ? hard_identity scenes ??3-reference ??? 0-reference ??? overall / view-match / detail ???identity fidelity ????????????? pilot evidence?????????? identity fidelity??

## Files

- `strict_group_summary.json/csv`: ??????????
- `strict_per_sample_results.jsonl/csv`: ?????????
- `paired_delta_summary.json/csv`: ??????
- `paired_scene_deltas.csv`: ?? scene ? 1-vs-0 / 3-vs-0 ??
- `view_bucket_summary.json/csv`: side/back/mixed ????
- `image_index.csv`: ????????????
- `excluded_*.jsonl`: ????????????
