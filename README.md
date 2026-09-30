# Jev Support

AI-assisted customer support: Jev (via BeatAPI) classifies tickets, deterministic rules decide what's allowed, OpenAI drafts the reply, and a support agent reviews it. See [project.md](project.md) for the full plan.

## Run locally

```bash
cp .env.example .env   # then fill in BEATAPI_API_KEY and OPENAI_API_KEY
docker compose up -d --build
curl localhost:8000/health
```

API docs: http://localhost:8000/docs
