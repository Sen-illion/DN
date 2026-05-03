# StoryDiffusion formal8 Image Quality Check

## Scope

- Run checked: `storydiffusion_formal8_unstable_20260430_1131`
- Local folder: `D:\Projects\DN\remote_baseline_results_20260430\outputs\storydiffusion_formal8\storydiffusion_formal8_unstable_20260430_1131`
- Images checked: 32 images = 8 samples x 4 scenes
- Contact sheet: `formal8_contact_sheet.png`
- Auto metrics: `formal8_image_quality_auto.csv`
- Manual notes: `formal8_manual_quality_notes.csv`

## Automatic Checks

- Black/NSFW-placeholder images: 0 flagged
- Blank/low-variance images: 0 flagged
- Tiny/corrupt files: 0 flagged
- Image dimensions: all generated images are readable PNGs

## Manual Visual Assessment

Overall: **technically usable but thematically weak**.

The formal8 output is valid as evidence that StoryDiffusion can run on DN-style inputs and produce multi-scene image sequences. However, it should not yet be treated as strong visual-quality evidence for the paper main table without manual caveats, because many themes collapse into a similar visual pattern: East-Asian lantern streets, window/interior compositions, and repeated solitary figures.

## Main Issues

- Strong style collapse across unrelated themes: sci-fi, apocalypse, clone ethics, and ancient temple samples often look like similar lantern-lit urban scenes.
- Theme grounding is weak for several prompts: moon mining, consciousness upload, greenhouse apocalypse, and star smuggling are not visually explicit.
- Character/scene consistency is reasonably stable, but that consistency comes partly from repeated composition and setting.
- No obvious black images, blank outputs, corrupt files, or severe generation failures were found.

## Sample-Level Notes

| ID | Theme | Rating | Notes |
|---|---|---|---|
| DNQBV1_001 | ??????? | pass with caveat | Coherent lighting and sequence; border relay station specificity is weak. |
| DNQBV1_002 | ?????? | weak | Missing apocalypse/greenhouse/gardener elements. |
| DNQBV1_004 | ?????? | weak | Clone/ethical tribunal theme not legible. |
| DNQBV1_005 | ?????? | weak | Moon/mining/disaster elements absent. |
| DNQBV1_006 | ?????? | weak | Some sci-fi sky impression, but smuggling/space route not clear. |
| DNQBV1_007 | ?????? | weak | Digital identity/upload/will theme absent. |
| DNQBV1_009 | ????? | pass with caveat | Tea/interior imagery fits better; still repetitive. |
| DNQBV1_010 | ?????? | weak | Ancient temple/bell tower/hidden treasure not clear. |

## Recommendation

Use this formal8 run as a **successful execution/efficiency baseline** and a qualitative appendix candidate, but do not claim strong semantic alignment. For a paper-facing visual table, either improve the prompt adapter with shorter English visual prompts and theme-specific keywords, or add a manual quality/alignment score column.
