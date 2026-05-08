# Setup Notes

## Environment

- venv:
  - `C:\Users\zhang\Desktop\DN\experiments\external_baselines\LIGHT\.venv-light`
- python:
  - `py -3.10`

## Installed packages

- `parlai==1.7.2`

## Notes

- the first checkpoint pull downloads roughly 1 GB of model assets from the ParlAI model zoo
- `pyarrow` had to be removed after install because Windows application-control policy blocked its DLL load and it was not required for the runnable inference path

## Smoke validation

- validated by loading:
  - `zoo:dodecadialogue/light_dialog_ft/model`
- and generating one reply from a manual prompt in local CPU mode
