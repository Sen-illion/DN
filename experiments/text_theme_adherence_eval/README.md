# Text Theme Adherence Eval (Offline)

- Model: `BAAI/bge-m3`
- Local model path: `D:\models\bge-m3`
- No OpenAI API key required.

## Install

```powershell
cd D:\DN-main\experiments\text_theme_adherence_eval
pip install -r requirements.txt
```

## Download model

```powershell
python evaluate_theme_adherence.py download --model-dir D:\models\bge-m3
```

## Evaluate one dataset

```powershell
python evaluate_theme_adherence.py evaluate ^
  --theme-csv examples\themes.csv ^
  --text-csv examples\texts_a.csv ^
  --neg-theme-file examples\negative_themes.txt ^
  --output-dir D:\embedding_eval_outputs
```

## Evaluate multiple datasets

```powershell
python evaluate_theme_adherence.py evaluate ^
  --theme-csv examples\themes.csv ^
  --text-csv examples\texts_a.csv ^
  --text-csv examples\texts_b.csv ^
  --neg-theme-file examples\negative_themes.txt ^
  --output-dir D:\embedding_eval_outputs
```

## Outputs

- `<dataset>_results.csv`
- `<dataset>_worst_topN.csv`
- `summary.csv`
- `comparison_by_margin_then_pass_rate.csv`
- `comparison_by_pass_rate_then_margin.csv`
- `global_worst_topN.csv`
- `run.log`
- `versions.json`
