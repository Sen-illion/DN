# DN Current Benchmark Stack

```mermaid
flowchart TD
    A["DN benchmark source<br/>experiments/benchmark/dn_quality_benchmark_v1.json"] --> B["DN native harness<br/>experiments/benchmark/benchmark_runner.py"]
    A --> C["Paper method view<br/>experiments/paper_method_view/"]
    C --> D["Table 1 main visual + efficiency"]
    C --> E["Table 2 text planning"]
    C --> F["Table 3 human evaluation"]
    C --> G["Ablations"]
    D --> H["DN raw runs / summary tables"]
    D --> I["Baselines/"]
    I --> J["baseline_genagents"]
    I --> K["baseline_storydiffusion"]
    I --> L["baseline_aidungeon"]
    I --> M["baseline integration layer<br/>experiments/baseline_integration/"]
    M --> N["schema/ unified run schema"]
    M --> O["adapters/ baseline-specific mapping"]
    M --> P["normalized_runs/ comparison-ready artifacts"]
    M --> Q["reports/ integration status and scaffold builders"]
```

## Current interpretation
- DN native benchmark harness is already the strongest runnable evaluation path
- paper-writing structure is separated from raw benchmark outputs
- external baselines are now being integrated through a normalization layer instead of being forced into one server API

## Current status by branch
- DN native runs: ready
- GenAgents: loader smoke passed, live inference pending API key
- StoryDiffusion: environment understood, blocked on current machine for real runs
- AIDungeon: conceptually strong, but legacy runtime makes it a later-priority execution target
