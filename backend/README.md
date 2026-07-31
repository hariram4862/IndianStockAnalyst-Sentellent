# Backend — Indian Stock Analyst

FastAPI backend: Google OAuth, stock ingestion (fundamentals + news → chunk → embed → pgvector),
and a LangGraph-based research/recommendation agent.

## Stack

FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL + pgvector · LangGraph · Google Gemini (chat +
embeddings, optional — falls back to keyword heuristics if no key is set) · yfinance · RSS news
feeds.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

cp .env.example .env     # fill in DATABASE_URL, JWT_SECRET, GOOGLE_CLIENT_ID/SECRET, GEMINI_API_KEY

alembic upgrade head
uvicorn app.main:app --reload
```

Needs a running Postgres with the `vector` extension available (the repo-root
`docker-compose.yml` provides one via `pgvector/pgvector:pg17` — the first Alembic migration
runs `CREATE EXTENSION IF NOT EXISTS vector`).

## Tests

```bash
pytest -v
```

Requires `DATABASE_URL` pointing at a migrated Postgres (see `tests/conftest.py`'s `db_session`
fixture) — the same database docker-compose or CI spins up works.

## Structure

- `app/services/agent_graph.py` — the LangGraph agent brain: intent/ticker extraction → persona
  memory update → persona-based stock ranking (recommend queries) → grounded retrieval →
  answer generation with an anti-hallucination guard.
- `app/services/stock_scoring.py` — deterministic, unit-tested persona-based stock ranking
  (no LLM call per stock).
- `app/services/ingestion_service.py` — chunk/embed/tag pipeline; idempotent (content-hash
  based) and concurrency-safe (Postgres advisory lock per ticker).
- `app/services/fundamentals_provider.py` / `news_provider.py` — yfinance + RSS sourcing.
- `app/api/routes/` — FastAPI routers (auth, stocks, research, health, users).
- `app/models/`, `app/schemas/` — SQLAlchemy models and Pydantic request/response shapes.
- `alembic/versions/` — schema migrations.
- `tests/` — pytest suite (scoring, agent-graph helpers, ingestion idempotency, citation guard,
  session history).
