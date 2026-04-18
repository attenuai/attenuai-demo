# Confused Deputy Showcase

Hackathon-ready boilerplate for a 3-act demo that shows how prompt injection can exploit an AI agent in insecure mode and how capability-style guardrails block the same attack path in secure mode.

## What is included

- `agent/` FastAPI backend, agent loop, tool dispatch, mock Gmail/calendar clients, and secure/insecure tool layers
- `frontend/` single-page split-screen UI for chat + live system monitor
- `content-server/` safe and malicious pages for the webpage attack path
- `mals-server/` live attacker dashboard that records exfiltrated requests
- `mock-data/` act-based inbox and calendar payloads
- `docs/` architecture notes and OAuth setup scaffolding

By default, the repo runs in a fully local **offline demo mode** with mock data and a deterministic planner so you can iterate without an API key. If you want to wire in OpenAI later, the scaffolding is already there.

## MVP runtime choice

For the MVP, we should keep **`AGENT_ENGINE=offline` as the default**.

Why:

- it is deterministic, so the 3-act demo is reproducible every run
- it keeps bootstrapping simple for judges and teammates
- it lets us validate the UI, event stream, and guard behavior before paying the complexity cost of a live model

`AGENT_ENGINE=openai` stays available as an optional upgrade path once the demo flow is stable.

## Verification

Run the smoke tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
.\.venv\Scripts\python.exe -B -m pytest tests -q
```

Run the real three-act boot check:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
.\.venv\Scripts\python.exe -B scripts\boot_check.py
```

## Quick start with Docker

1. Copy the env template:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start the full stack:

   ```powershell
   docker compose up --build
   ```

3. Open:

- App UI: [http://localhost:8000](http://localhost:8000)
- Content server: [http://localhost:8081](http://localhost:8081)
- Exfil dashboard: [http://localhost:8082](http://localhost:8082)

## Mode switching

The app starts in insecure mode by default. Use the Secure/Insecure toggle in the chat header to switch modes while the app is running.

## Local development without Docker

Open three terminals from the repo root.

### Terminal 1: content server

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r content-server\requirements.txt
uvicorn server:app --app-dir content-server --reload --host 0.0.0.0 --port 8081
```

### Terminal 2: mals server

```powershell
.venv\Scripts\Activate.ps1
pip install -r mals-server\requirements.txt
uvicorn server:app --app-dir mals-server --reload --host 0.0.0.0 --port 8082
```

### Terminal 3: agent app

```powershell
.venv\Scripts\Activate.ps1
pip install -r agent\requirements.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:USE_MOCK_DATA="1"
$env:AGENT_ENGINE="offline"
uvicorn main:app --app-dir agent --reload --host 0.0.0.0 --port 8000
```

## OpenAI mode

The app can optionally use the Chat Completions API instead of the offline planner.

```powershell
$env:AGENT_ENGINE="openai"
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-4o-mini"
uvicorn main:app --app-dir agent --reload --host 0.0.0.0 --port 8000
```

Notes:

- The offline planner is what makes the repo runnable immediately.
- The secure tool layer currently uses a local capability-style shim so the demo works out of the box.
- `agent/tools_secure.py` is the handoff point for swapping in real Tenuo decorators and warrant minting.

## Suggested demo prompts

- `Summarize my new emails`
- `Check my calendar and flag anything unusual`
- `Read http://localhost:8081/pages/acme-q2-report.html and summarize it`
- `Read http://localhost:8081/pages/mal-ai-trends.html and summarize it`

## Repo structure

```text
agent/
frontend/
content-server/
mals-server/
mock-data/
docs/
scripts/
```
