# DN vs Paper Image Consistency Baselines

| Group | Planned | Scored | Coverage | Overall | Semantic | Subject Attr | Spatial | Style/Lighting | Detail | Delta vs DN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dn_ours | 9 | 9 | 1.0000 | 9.2222 | 9.8889 | 9.2222 | 9.2222 | 9.6667 | 9.2222 | 0.0000 |
| naive_t2i | 9 | 7 | 0.7778 | 7.0000 | 7.7143 | 6.8571 | 7.0000 | 7.1429 | 7.2857 | -2.2222 |
| prompt_only_memory | 9 | 9 | 1.0000 | 9.0000 | 10.0000 | 9.0000 | 9.0000 | 9.5556 | 9.0000 | -0.2222 |
| visual_bible | 9 | 9 | 1.0000 | 9.0000 | 10.0000 | 9.0000 | 9.0000 | 9.8889 | 9.0000 | -0.2222 |
| prompt_plus_prev_image | 9 | 7 | 0.7778 | 9.1429 | 10.0000 | 9.1429 | 9.1429 | 9.4286 | 9.1429 | -0.0793 |

Notes:
- Scores use the same gpt-4o judge path as the DN image-consistency evaluator.
- Only 9 of the requested 10 source themes were eligible because theme 006 lacks prompt/image material for segment 2 in the current DN source dataset.
- naive_t2i and prompt_plus_prev_image have lower coverage because several image-generation API calls failed or timed out.