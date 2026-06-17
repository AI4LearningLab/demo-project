# Socratic Debug Tutor

A history-aware Socratic prompt wrapper that develops debugging skills in
undergraduate software engineers. The system tracks each student's past
struggles, mastery scores, and behaviour patterns, then transforms every
prompt before it reaches the LLM so responses are Socratic and personalised —
never just "here's the answer".

---

## Architecture at a glance

```
Frontend (React)
    ↓  REST
API Gateway (FastAPI)
    ↓
Core Services
  ├── PromptTransformer   ← core research contribution
  ├── ContextBuilder      ← RAG: pgvector + mastery DB
  ├── ProgressService     ← mastery score updates
  └── SM2Service          ← spaced repetition scheduler
    ↓
LLM Layer (Ollama — runs locally)
    ↓
Data Layer
  ├── PostgreSQL + pgvector
  └── Redis (session cache)
```

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | |
| Node.js | 20+ | for frontend |
| Docker + Compose | latest | for Postgres & Redis |
| Ollama | latest | https://ollama.com — runs locally |

---

## Quick start

### 1. Clone and configure

```bash
git clone <repo>
cd socratic-debug

# Backend config
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set APP_SECRET_KEY and JWT_SECRET_KEY
```

### 2. Pull your Ollama model

```bash
# Make sure Ollama is running, then pull the model
ollama pull llama3.2

# Verify it works
ollama run llama3.2 "Hello"
```

### 3. Start infrastructure (Postgres + Redis)

```bash
docker compose up postgres redis -d
```

### 4. Install backend dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run database migrations

```bash
# Enable pgvector extension first (run once)
docker exec -it socratic-debug-postgres-1 psql -U socratic -d socratic_debug \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Apply migrations
alembic upgrade head
```

### 6. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 7. Run tests

```bash
pytest tests/unit/ -v              # unit tests (no DB needed)
pytest tests/ -v --cov=app         # all tests with coverage
```

---

## Project structure

```
socratic-debug/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   └── progress.py
│   │   ├── core/
│   │   │   ├── config.py        # all env vars — single source of truth
│   │   │   ├── auth.py          # JWT + password utils
│   │   │   └── logging.py       # structured logging
│   │   ├── db/
│   │   │   └── session.py       # async SQLAlchemy session
│   │   ├── models/
│   │   │   └── models.py        # all ORM models
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   └── services/
│   │       ├── llm/
│   │       │   ├── ollama_service.py    # LLM abstraction
│   │       │   └── embedding_service.py # pgvector embeddings
│   │       ├── context/
│   │       │   └── context_builder.py  # RAG pipeline
│   │       ├── prompt/
│   │       │   └── prompt_transformer.py  # CORE CONTRIBUTION
│   │       ├── reminder/
│   │       │   └── sm2.py              # spaced repetition
│   │       ├── progress/
│   │       │   └── progress_service.py # mastery updates
│   │       └── chat_service.py         # orchestrator
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_sm2.py
│   │   │   └── test_prompt_transformer.py
│   │   └── integration/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                    # React app (next step)
├── docker-compose.yml
└── README.md
```

---

## Key design decisions

### Why Ollama (local LLM)?
- No API cost during research / development
- Data stays on your machine (important for student data)
- Swap to Claude/GPT by changing `ollama_service.py` — the interface is identical

### Why pgvector instead of Pinecone?
- Runs inside your existing Postgres — no extra service
- Good enough for research scale (< 100k sessions)
- Upgrade to Pinecone later by swapping `embedding_service.py` only

### Why SM-2 from scratch?
- Adds to research contribution
- We apply it to debugging sub-skills, not vocabulary — a genuine novel use

### Mastery score formula
```
solved_no_hints    → +0.10
solved_with_hints  → +0.05
failed_after_hints → -0.10
repeated_mistake   → -0.15
```
Clamped to [0.0, 1.0]. Review threshold: < 0.5 = weak area.

---

## Extending the system

### Add a new bug type
In `app/services/context/context_builder.py`, add to `PREREQUISITE_MAP`:
```python
"your_new_bug": ["concept_a", "concept_b"],
```

### Swap the LLM
In `app/services/llm/ollama_service.py`, change `ChatOllama` to any LangChain
chat model (e.g. `ChatAnthropic`, `ChatOpenAI`). The rest of the system is
unaffected.

### Add a new route
1. Create `app/api/routes/your_route.py`
2. Add schemas to `app/schemas/schemas.py`
3. Register in `app/main.py`: `app.include_router(your_route.router, prefix="/api/v1")`
