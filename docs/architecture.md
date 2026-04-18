# Architecture

```mermaid
flowchart LR
  User["User in browser"] --> Agent["FastAPI agent app (:8000)"]
  Agent --> Frontend["Static frontend"]
  Agent --> Content["Content server (:8081)"]
  Agent --> Exfil["Exfil server (:8082)"]
  Agent --> Mock["Mock data"]
```

## Runtime modes

- The UI toggle switches between insecure raw tool execution and secure guarded tool execution.
- Mock data is loaded from a single default dataset in `mock-data/`.
- `AGENT_ENGINE=offline`: deterministic local planner for development
- `AGENT_ENGINE=openai`: Chat Completions tool-calling flow

## Security handoff point

`agent/tools_secure.py` currently implements local capability-style checks so the demo runs without extra dependencies or secret material. Swap those guards for real Tenuo warrant decorators when you are ready to integrate the production security layer.
