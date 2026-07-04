# AGENTS.md

## Cursor Cloud specific instructions

This repo hosts two co-located products under `src/`:

- **Product A — NestJS API (`atlas-local`)**: TypeScript RAG/document-intelligence API. Entry `src/main.ts`. Requires a reachable MongoDB (`MONGODB_URI`).
- **Product B — Python CLI (`python -m src.main`)**: self-contained batch indexer/reporter over local DuckDB/SQLite (`data/*.db`). Independent from MongoDB.

The update script installs Node deps (`npm ci`) and Python deps into `.venv`. Below are the non-obvious caveats for running/testing.

### MongoDB (required for the NestJS API)
- Docker is NOT available in this environment, so the `docker compose` flow in the README does not apply. A local MongoDB Community `mongod` (v8) is installed instead.
- Start it (no auth, dev only) before running the API or if it is not already running:
  `mongod --dbpath /data/db --bind_ip 127.0.0.1 --port 27017` (run in a tmux/background session).
- Vector search is disabled by default (`ATLAS_VECTOR_SEARCH_ENABLED=false`), so plain community `mongod` is sufficient. The Atlas-specific vector index in `mongo-init-scripts/` is only needed when vector search is enabled.

### Environment file (`.env`, gitignored)
- Both products read `.env`. Create one for local dev if missing.
- Use `MONGODB_URI=mongodb://127.0.0.1:27017/atlas_local_db` for the local `mongod` above.
- `INDEX_ASYNC_DRIVER` must be `event_emitter` or `bullmq` (Zod enum). The value `sync` shown in `.env.example` FAILS validation — do not use it.
- `.env.example` uses placeholder Mongo passwords that only make sense for the Docker Atlas image; ignore them for the local `mongod` setup.

### Groq LLM key (`GROQ_API_KEY`)
- NestJS API boots and serves all non-LLM endpoints (knowledge index/search, health, metrics, planner, tabular) WITHOUT a key.
- The Python CLI validates `GROQ_API_KEY` as non-empty at startup even for offline commands (`index`, `report`). A placeholder value passes validation; `index`/`report` never call Groq. Only `ask`/RAG actually call the API and need a REAL key.

### Run / build / test (standard commands live in `package.json`, `pyproject.toml`, `README.md`)
- API dev server: `npm run start:dev` → http://localhost:3000, Swagger at `/api`, health at `/health`.
- Jest unit: `npm test`. E2E: `NODE_ENV=test npm run test:e2e` (uses `mongodb-memory-server`, needs no external Mongo).
- Python tests: activate `.venv`, then `python -m pytest tests/`.
- Python CLI: `python -m src.main index --path <dir> --db-path data/<name>.db`. Add `--isolate-flags ""` to skip aggressive corpus remediation that would otherwise isolate short/repetitive demo docs.

### Known pre-existing failures (present on `main`, NOT environment issues)
- `npm run lint` is broken: `eslint.config.js` requires the `typescript-eslint` package which is missing from `package.json` devDependencies; even after installing it, there are ~199 pre-existing lint errors (tsconfig excludes `test/**`, plus strict-type-checked violations). CI does not run lint.
- Python tests: 5 tests in `tests/test_async_llm.py` fail because `pytest-asyncio` is not declared in `requirements.txt` (`async def functions are not natively supported`). This also fails in CI on `main`.
- E2E: `test/smoke-s10.e2e-spec.ts` "health endpoints should not be rate-limited" fails with `ECONNRESET` (fires concurrent `/health` requests). Pre-existing; CI e2e also fails on `main`.
