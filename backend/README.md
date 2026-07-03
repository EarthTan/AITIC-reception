# AITIC 展厅智能前台 · backend

Python 3.13+, dependency management via [uv](https://docs.astral.sh/uv/).

## Run

```bash
uv run main.py            # FastAPI on http://localhost:8000, Swagger UI at /docs
```

## Test

```bash
uv run pytest                                  # full suite: 72 pass + 1 documented-acceptable fail
uv run pytest -v                               # verbose listing
uv run pytest tests/test_X.py                  # one file
uv run pytest -k test_name                     # one test by name
uv run pytest -k "not test_get_work_logs_does_not_leak_unmasked_id_numbers"  # skip the known-red PII guard
```

Test pattern: in-memory SQLite per test, fresh `EventBus()` per test, mock adapters throughout. The Day-2 `tests/conftest.py` autouse fixture wipes `data/settings_override.json` between tests so the persisted settings don't leak.

## Project layout

```
app/
├── core/        # Config, DB engine, EventBus, logging, backup, seed, settings_store
├── models/      # 6 SQLAlchemy ORM models
├── schemas/     # 7 Pydantic modules (request/response shapes)
├── services/    # 6 business services — all event-bus driven, no cross-imports
├── adapters/    # 4 abstract + 4 mock + 1 real (QwenAIAdapter); real NFC/LED/TTS pending
├── api/         # 9 FastAPI routers + deps.py (see CLAUDE.md for endpoint list)
├── watchers/    # ExcelWatcher (watchdog)
└── main.py      # build_app composition root + uvicorn shim
```

## Common tasks

```bash
# Re-export the OpenAPI snapshot at docs/openapi.json
uv run python -c "import json; from app.main import build_app; \
  json.dump(build_app().openapi(), open('../docs/openapi.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"

# Add a dependency (uv manages pyproject.toml + uv.lock; never pip/poetry directly)
uv add packagename
```

## Gitignored state

The `data/` directory is in `.gitignore`. It contains:
- `app.db` — the SQLite database (created on first `build_app` run)
- `settings_override.json` — persisted settings from `PUT /api/settings`
- `pending_imports/` — staged Excel files between `/api/import/preview` and `/api/import/commit`
- `incoming/` — watched by `ExcelWatcher` for auto-detect (`excel.detected` events)
- `backup/` — daily APScheduler backups (02:00)

If the override file or a stale `pending_imports/*.xlsx` causes tests to misbehave, delete the file and re-run.

## Dev quirks

See [`../CLAUDE.md`](../CLAUDE.md) §"Known dev quirks" for the full list. The big four for backend work:

1. `MockNFCAdapter` is the **only** adapter with `simulate_card_read` — `MockAIAdapter` does not.
2. `QwenAIAdapter(...) if settings.ai_api_key else MockAIAdapter()` constructs the real client eagerly. On SOCKS-proxied dev boxes, `httpx[socks]>=0.28.1` (already in `pyproject.toml`) is required.
3. The 1 red test in `tests/test_api_logs.py::test_get_work_logs_does_not_leak_unmasked_id_numbers` is **intentional** — it guards the writer-level PII rule by seeding a synthetic leak row.
4. The uvicorn module-level shim (`__getattr__` in `app/main.py`) defers `app` construction; tests import `build_app` directly to avoid it.
