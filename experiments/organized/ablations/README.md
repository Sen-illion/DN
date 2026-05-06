# Ablation Experiments

Controlled variants that isolate specific modules or settings.

## Contents

- `01_council_ablation`: Council Ablation ? no_council is faster for worldview-only repeated runs, but full-chain default has better success reliability.
- `02_pregeneration_ablation`: Pregeneration Ablation ? Clean v3 runs show pregen_on reduces worldview mean versus pregen_off, while option latency differences are tiny by median.
- `03_text_ablation`: Text Ablation ? Both modules on gives the best cleaned cross-condition average; turning both off is worst.
- `04_generation_context_ablation`: Generation Context Ablation ? dn_ours is best, prompt_plus_prev_image is close, naive_t2i is clearly weaker.
- `05_protagonist_reference_ablation`: Protagonist Reference Ablation ? Three references are slightly better on strict hard-identity subset, but ordinary set does not show a strong monotonic gain.
- `06_readwait_ablation`: Read Wait Ablation ? Current artifact set is partial and should be treated as exploratory only.
