# GPT-executable task: run DOC as the DN text baseline

## Objective

Use the external paper baseline **DOC Story Generation V2** as the text-generation baseline for the DN project. Do not treat DN module-off experiments as the baseline. The baseline must run on the same DN themes and be exported into the same manifest/segment layout used by DN's text evaluator.

## Repository context

- DN repo root: `C:\Users\User\Desktop\DN-main`
- DOC repo: `C:\Users\User\Desktop\DN-main\external\doc-storygen-v2`
- DN theme file: `C:\Users\User\Desktop\DN-main\game_themes_100.json`
- DOC adapter script: `C:\Users\User\Desktop\DN-main\experiments\baselines\doc_baseline\run_doc_on_dn.py`
- DN text evaluator: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\eval_plot_coherence.py`

## API requirement

DOC must use the user's Yunwu/OpenAI-compatible API instead of a local vLLM server.

The DOC LLM client has been patched at:

`C:\Users\User\Desktop\DN-main\external\doc-storygen-v2\storygen\common\llm\llm.py`

It now reads API settings in this priority order:

- API key: `DOC_OPENAI_API_KEY`, `YUNWU_API_KEY`, `COHERENCE_API_KEY`, `Origin_Segment_Analyst_API_KEY`, `OPENAI_API_KEY`
- Base URL: `DOC_OPENAI_BASE_URL`, `OPENAI_BASE_URL`, `YUNWU_BASE_URL`, `COHERENCE_BASE_URL`, `Origin_Segment_Analyst_BASE_URL`, fallback `https://api.openai.com/v1`

Use `server_type: openai` and `prompt_format: openai-chat`; do not start vLLM.

## Baseline definition to preserve

Text baseline name: `DOC`

Definition:

> DOC baseline generates a long story from each DN theme using the DOC premise-plan-story pipeline. The generated story is split into the same number of DN-style segments and evaluated with the same coherence evaluator as DN outputs.

## Execution steps

1. Confirm DOC dependencies are installed in its environment. If not installed, install inside the DOC repo:

```powershell
cd C:\Users\User\Desktop\DN-main\external\doc-storygen-v2
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

2. Run a one-theme smoke test first:

```powershell
$ROOT="C:\Users\User\Desktop\DN-main"
$PY="$ROOT\.venv2\Scripts\python.exe"
$DOC_PY="$ROOT\external\doc-storygen-v2\.venv\Scripts\python.exe"

& $PY "$ROOT\experiments\baselines\doc_baseline\run_doc_on_dn.py" `
  --doc-python $DOC_PY `
  --theme-ids 1 `
  --max-themes 1 `
  --segments 10 `
  --stable-no-logprobs `
  --output-root "$ROOT\experiments\baselines\text_doc_smoke"
```

3. If the smoke test succeeds, score the DOC baseline:

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\experiments\baselines\text_doc_smoke" `
  --runs 3 `
  --output "$ROOT\experiments\baselines\text_doc_smoke\coherence_doc_smoke.xlsx"
```

4. Run the full DOC baseline over the preset DN themes:

```powershell
& $PY "$ROOT\experiments\baselines\doc_baseline\run_doc_on_dn.py" `
  --doc-python $DOC_PY `
  --theme-ids "1,2,3,4,5,6,12,18,54,73" `
  --segments 10 `
  --stable-no-logprobs `
  --output-root "$ROOT\experiments\baselines\text_doc"
```

5. Score the full DOC baseline:

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\experiments\baselines\text_doc" `
  --runs 3 `
  --output "$ROOT\experiments\baselines\text_doc\coherence_doc.xlsx"
```

6. Score the DN method on the same evaluator for comparison:

```powershell
& $PY "$ROOT\DN-experiment-2.0\eval_plot_coherence.py" `
  --dataset "$ROOT\DN-experiment-2.0" `
  --runs 3 `
  --output "$ROOT\experiments\baselines\text_doc\coherence_dn.xlsx"
```

## Notes

- Use `--stable-no-logprobs` for Yunwu or other API providers that do not reliably support token logprobs in chat completions.
- If the chosen API supports logprobs and DOC reranking is required, remove `--stable-no-logprobs`.
- The adapter exports DOC outputs into DN-compatible folders under the chosen `--output-root`.
- Each output folder contains `doc_premise.json`, `doc_plan.json`, `doc_story.txt`, a DN-style manifest, and per-segment JSON files.

## Expected final answer

After running, report:

- whether DOC generation succeeded
- output root path
- number of generated DOC baseline games
- coherence workbook path
- any API/logprob errors
- whether comparison against DN outputs was completed
