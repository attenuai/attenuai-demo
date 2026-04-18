# Repository Guidelines

## Project Structure & Module Organization
This repo is a local demo stack for the "Confused Deputy Showcase". Core application code lives in `agent/` (FastAPI app, agent loop, tool layers, config). The browser UI is a static frontend in `frontend/` with `index.html`, `style.css`, and `app.js`, served by the agent app. Supporting services live in `content-server/` and `mals-server/`. Test coverage is in `tests/`, mock inbox/calendar payloads are in `mock-data/`, and operational notes live in `docs/`. Use `scripts/boot_check.py` for end-to-end startup verification.

## Build, Test, and Development Commands
Run the full stack with `docker compose up --build`.
Run the Python smoke tests with `python -B -m pytest tests -q`.
Run the startup check with `python -B scripts/boot_check.py`.
For local development, create one virtualenv at repo root and install per-service requirements:
`pip install -r agent/requirements.txt`
`pip install -r content-server/requirements.txt`
`pip install -r mals-server/requirements.txt`
Then start services with `uvicorn main:app --app-dir agent --reload --port 8000` and `uvicorn server:app --app-dir <service> --reload --port <port>`.

## Coding Style & Naming Conventions
Follow the existing style: Python uses 4-space indentation, type hints, dataclasses where useful, and `snake_case` for functions, modules, and variables. Frontend JavaScript also uses 2-4 space readable indentation, `const`/`let`, and `camelCase` for function names like `appendMonitor()`. Keep files focused by service boundary instead of mixing agent, content, and exfil concerns. No formatter or linter config is checked in, so match surrounding code closely and keep imports/order tidy.

## Testing Guidelines
Use `pytest`; the repo disables the cache provider via `pytest.ini`. Add tests under `tests/` as `test_*.py`, mirroring the current `tests/test_smoke.py` pattern. Prefer deterministic tests with `monkeypatch`, mocked network calls, and explicit environment setup through `tests/helpers.py`. Cover both insecure and secure flows when changing tool behavior or policy checks.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects such as `Add docs` and `new changes`; prefer clearer summaries like `Add secure webpage exfil smoke test`. Keep commit titles under about 72 characters. PRs should describe the user-visible behavior change, note config or env changes, link the relevant issue, and include screenshots or short recordings when UI behavior changes.

## Configuration Notes
Default development mode is offline: set `AGENT_ENGINE=offline` and `USE_MOCK_DATA=1`. Copy `.env.example` to `.env` before local runs, and never commit real API keys or OAuth credentials.
