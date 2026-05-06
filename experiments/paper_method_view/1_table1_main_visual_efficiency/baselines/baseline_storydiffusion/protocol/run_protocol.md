# Run Protocol

## Intended comparison scope
- DN multimodal and visual-consistency comparison
- visual-quality support for Table 1 rather than a full interactive-game comparison

## Planned benchmark mapping
- task source: `DN-quality-benchmark-v1`
- smoke-test subset: `protocol/storydiffusion_smoke_subset_v1.json`
- main visual subset: `protocol/storydiffusion_visual_subset_v1.json`
- main visual subset size: 6
- mode: multimodal subtask

## Subset design
### Smoke-test subset
- `DNQBV1_001` realistic: confirm basic story-to-image generation under a grounded visual style
- `DNQBV1_015` anime: confirm style transfer behavior under a more stylized visual regime

### Main visual subset
The main subset uses one representative benchmark item per style family so that StoryDiffusion is not over-fitted to only one visual mode.
- realistic: `DNQBV1_001`
- cyberpunk: `DNQBV1_005`
- ink_painting: `DNQBV1_009`
- watercolor: `DNQBV1_012`
- anime: `DNQBV1_015`
- oil_painting: `DNQBV1_018`

## Expected StoryDiffusion input mapping
For each benchmark item, prepare:
- one short story brief derived from the benchmark theme and expected tone
- at least 3 scene prompts for StoryDiffusion comic generation
- style prompt aligned with the benchmark `image_style.type`

## Normalized outputs required
- benchmark id
- style type
- generated image set
- scene text / prompt bundle used for generation
- success / failure status
- latency
- failure reason if any

## Evaluation targets
Primary targets for this baseline:
- visual consistency
- character consistency across scenes
- text-image alignment
- image usable rate

Not primary targets for this baseline:
- branching gameplay quality
- interactive option usefulness
- pregeneration / read-wait system efficiency

## Notes
- This protocol should not be presented as a full interactive-game comparison unless the baseline truly supports that flow.
- If local hardware cannot support the full 6-sample subset, keep the smoke subset as a gate and document the limitation in `status.md`.
- Current execution decision:
  - on the present Windows machine, stop before Stage 2
  - only resume this protocol on a CUDA-capable machine after the same environment is recreated
