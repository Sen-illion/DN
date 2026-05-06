# GPT-executable task: run Rolling-4o as the DN text baseline

## Baseline location

Rolling-4o is a local baseline runner, not an external repository.

- Runner: `C:\Users\User\Desktop\DN-main\experiments\baselines\rolling_4o\run_rolling_4o.py`
- Theme file: `C:\Users\User\Desktop\DN-main\game_themes_100.json`
- Output root: `C:\Users\User\Desktop\DN-main\experiments\baselines\text_rolling_4o`
- Evaluator: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\eval_plot_coherence.py`

## Baseline definition

Rolling-4o generates 10 story segments per theme. Segment 1 receives only theme and style. Segments 2-10 receive only theme, style, the rolling summary, and the previous segment. After every segment, the same model compresses the story so far into a <=200 Chinese-character summary.

It does not use DOC planning, images, GPU, or Replicate.

## Smoke test

```powershell
$ROOT="C:\Users\User\Desktop\DN-main"
$PY="$ROOT\.venv2\Scripts\python.exe"

& $PY "$ROOT\experiments\baselines\rolling_4o\run_rolling_4o.py" `
  --theme-ids 1,2,3 `
  --segments 10 `
  --overwrite `
  --output-root "$ROOT\experiments\baselines\text_rolling_4o_smoke"
```

## Score smoke test

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\experiments\baselines\text_rolling_4o_smoke" `
  --runs 1 `
  --output "$ROOT\experiments\baselines\text_rolling_4o_smoke\coherence_rolling_smoke.xlsx"
```

## Full run

This runs all 100 themes and makes about 2,000 chat-completion calls: 100 themes x 10 segments x 2 calls (segment + summary).

```powershell
& $PY "$ROOT\experiments\baselines\rolling_4o\run_rolling_4o.py" `
  --theme-ids 1-100 `
  --segments 10 `
  --resume `
  --output-root "$ROOT\experiments\baselines\text_rolling_4o"
```

## Score full run

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\experiments\baselines\text_rolling_4o" `
  --runs 3 `
  --output "$ROOT\experiments\baselines\text_rolling_4o\coherence_rolling.xlsx"
```

## Score DN on the same evaluator

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\DN-experiment-2.0" `
  --runs 3 `
  --output "$ROOT\experiments\baselines\text_rolling_4o\coherence_dn.xlsx"
```

## Expected outputs per theme

- `theme_<id>_theme\story.txt`
- `theme_<id>_theme\summary_trace.json`
- `theme_<id>_theme\segments\001.json` through `010.json`
- `theme_<id>_theme\rolling_theme_<id>_manifest.json`
- `theme_<id>_theme\run_meta.json`

