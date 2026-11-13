# Host

Python program that reads samples from the board over the ST-LINK virtual COM port and plots them live.

## Setup

On Windows, from this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Development

```powershell
pytest              # run the tests
ruff format .       # format
ruff check .        # lint
```
