# Confused Deputy Showcase

This project demonstrates an AI agent that is intentionally vulnerable to prompt injection attacks and an easy method to minimize or eliminate damage by using Capabilities-Based security, in this case, using [tenuo](https://github.com/tenuo-ai/tenuo). The agent can use OpenAI (you supply the API key) or a local LLM. It has only been tested in Docker.

[Video demo](https://www.youtube.com/watch?v=ihNMMc6LrSc)

## Quick start

```
git clone https://github.com/attenuai/attenuai-demo.git
cp .env.example .env
```

Change OPENAI_BASE_URL_LOCAL to "http://host.docker.internal:11434/v1". The model that consistently fell victim to tge prompt injection demo was GPT-OSS 20b. I don't know if that's because of the model or because I finally fixed all the other things in the code at the same time I tested that model. Maybe other models are more vulnerable, I don't really know.

The UI allows you to change the model while it is running. The .env just specifies the default model.

```
docker compose up
```

Open:

- Content server: [http://localhost:8081](http://localhost:8081)
- Exfil dashboard: [http://localhost:8082](http://localhost:8082)
- AI Chatbot: [http://localhost:8000](http://localhost:8000)

The app starts in insecure mode by default. Use the Secure/Insecure toggle in the chat header to switch modes while the app is running.

## What is included

- `agent/` FastAPI backend, agent loop, tool dispatch, and secure/insecure tool layers
- `frontend/` single-page split-screen UI for chat + live system monitor
- `content-server/` safe and malicious pages for the webpage attack path
- `mals-server/` live attacker dashboard that records exfiltrated requests
- `mock-data/` local demo data and support files
- `docs/` architecture notes
