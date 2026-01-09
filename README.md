# Phobos

Minimal scaffold to kick off development.

## Project Layout
- [app/](app/) — application code
	- [app/services/](app/services/) — service modules (rclone, cleaner, db)
	- [app/daemon/](app/daemon/) — watcher/daemon logic
	- [app/api/](app/api/) — FastAPI app modules
	- [app/cli.py](app/cli.py) — CLI entrypoint
- [tests/](tests/) — test suite
- [.env.example](.env.example) — environment template
- [requirements.txt](requirements.txt) — dependencies
- [Dockerfile](Dockerfile) — container image

## Quick Setup
Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Development
See [docs/](docs/) for detailed specifications and architecture.