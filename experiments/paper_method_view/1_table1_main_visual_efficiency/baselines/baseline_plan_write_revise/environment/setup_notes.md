# Environment Notes

Recommended environment bootstrap for this baseline:

```powershell
cd C:\Users\zhang\Desktop\DN\experiments\external_baselines\plan_write_revise
py -3.10 -m venv .venv-pwr
.\.venv-pwr\Scripts\Activate.ps1
pip install --upgrade pip
pip install flask flask-cors requests
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

If the original pinned versions fail on the current machine, keep the adapter code unchanged and document any dependency substitutions in this folder before running benchmark data.


## Actual compatibility fixes used on this machine
- Python 3.10 virtual environment was used.
- `PYTHONUTF8=1` was required during installs to avoid GBK decode failures.
- official model pack was downloaded via `gdown` from the Google Drive folder in the upstream README.
- `pytorch_src/utils.py` was patched to:
  - fall back from `en_core_web_lg` to `en_core_web_sm`
  - import `ORTH` explicitly for SpaCy special tokens
  - patch old ASGD optimizer state loading
  - restore missing LSTM compatibility fields before moving the model to CPU
- `server/system2.py` was patched to:
  - fall back to whitespace detokenization when Moses/Perl tooling is missing on Windows
  - default `kw_temp` to the model config when the API omits it
- local WordNet data was placed under `experiments/external_baselines/plan_write_revise/nltk-data/`.
