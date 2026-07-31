# Indian Stock Analyst — Contextual Agentic AI (RAG)

A personal AI equity-research assistant for the NSE/BSE. Follow Indian stock tickers, the app
ingests their fundamentals and recent news into a vector store, and you chat with a LangGraph
agent that answers with cited, grounded sources — never a number it can't point to.

**Live app**: https://app.stocks.hariram.me
**API**: https://api.stocks.hariram.me

## What it does

- **Google OAuth login**, then follow any NSE ticker (e.g. `RELIANCE`, `TCS`, `INFY`) — the
  backend fetches fundamentals (yfinance) and recent news (RSS from Economic Times, LiveMint,
  Business Standard), chunks and embeds it into Postgres/pgvector, and tags each article's
  sentiment/impact/event with an LLM pass.
- **Chat** with the agent: ask about a stock's sentiment, fundamentals, or recent news, and it
  retrieves the most relevant chunks and answers with numbered citations, in INR. If nothing's
  been ingested for what you asked, it says so instead of inventing an answer.
- **Dynamic investor persona**: tell it things like "I'm a conservative, dividend-focused
  investor and I avoid high-debt companies," and it remembers — persisted per user, updated on
  every relevant message.
- **Personalized recommendations**: ask it to recommend stocks and it ranks your followed
  tickers against your persona (value/stability/momentum, weighted by risk profile) using
  deterministic scoring logic — not an LLM call per stock.

## Architecture

```
Namecheap (hariram.me) --NS delegation--> Route53 (stocks.hariram.me)
                                              |
                                    ALB (HTTPS, host-based routing)
                                    /                          \
                    app.stocks.hariram.me              api.stocks.hariram.me
                    ECS Fargate: Next.js            ECS Fargate: FastAPI + LangGraph agent
                                                              |
                                                    RDS Postgres + pgvector
                                                    (fundamentals, news chunks,
                                                     chat history, persona memory)

GitHub Actions: push to main -> test -> build & push images (ECR) ->
                register new task defs -> run DB migration -> deploy (ECS)
```

The agent brain (`backend/app/services/agent_graph.py`) is a LangGraph `StateGraph`: extract
intent/tickers → update persona memory (LLM-structured extraction) → rank stocks
(deterministic, persona-recommend queries only) → retrieve grounded sources (pgvector cosine
search) → generate an answer, with a structural anti-hallucination guard that refuses before
ever calling the LLM if there's no grounded source for the question.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), Tailwind v4, TypeScript |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Agent / RAG | LangGraph, Google Gemini (chat + embeddings), pgvector |
| Database | PostgreSQL + pgvector on RDS |
| Infra | Terraform (VPC, ECS Fargate, RDS, ALB, Route53/ACM, ECR, Secrets Manager) |
| CI/CD | GitHub Actions |
| Auth | Google OAuth |

## Repo layout

- `backend/` — FastAPI app, LangGraph agent, Alembic migrations, tests. See `backend/README.md`.
- `frontend/` — Next.js app. See `frontend/README.md`.
- `infrastructure/` — Terraform for the full AWS stack. See `infrastructure/README.md` for setup,
  cost profile, and known limitations/trade-offs made under deadline pressure.
- `.github/workflows/deploy.yml` — CI/CD pipeline.
- `docker-compose.yml` — full local stack (Postgres/pgvector + backend + frontend) for development.

## Running locally

```bash
docker compose up --build
```

Brings up Postgres (with pgvector), runs Alembic migrations, and starts both the backend
(`:8000`) and frontend (`:3000`). Needs a `backend/.env` (copy `backend/.env.example`) with a
Google OAuth client ID/secret and a Gemini API key — the app runs without a Gemini key too,
falling back to keyword-based sentiment tagging and template answers, just without LLM-quality
grounding/persona extraction.
