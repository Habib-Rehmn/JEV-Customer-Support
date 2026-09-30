# Jev Support

AI-assisted customer support: Jev (via BeatAPI) classifies tickets, deterministic rules decide what's allowed, OpenAI drafts the reply, and a support agent reviews it.

## Run locally

```bash
cp .env.example .env   # then fill in BEATAPI_API_KEY and OPENAI_API_KEY
docker compose up -d --build
docker compose exec backend python -m scripts.seed   # demo customers + orders
curl localhost:8000/health
```

- App: http://localhost:3000 (customer form at `/support`, agent login at `/login`)
- API docs: http://localhost:8000/docs

## Users

Customers submit tickets without an account (`POST /api/v1/tickets`). Everything else needs a support user:

```bash
docker compose exec backend python -m scripts.create_user --name "Admin" --email admin@example.com --role ADMIN
```

Log in with `POST /api/v1/auth/login` and send the token as `Authorization: Bearer <token>`.
Admins can add agents with `POST /api/v1/users`.

## Tests

```bash
docker compose exec backend pytest
```
