# backend/tests/conftest.py
"""Session/test fixtures that guard against cross-test state pollution.

Task 14 makes `build_app` load `data/settings_override.json` at startup so that
the persisted settings (PUT /api/settings) are honoured on the next request.
The settings-API tests in `test_api_settings.py` round-trip an override file
at that path, which would otherwise leak into the next test that calls
`build_app(...)` (including a subsequent test in the same file).

The two test files in `test_api_settings.py` use tmp_path-isolated SQLite
databases, but the override file path is hardcoded in `build_app` to
`data/settings_override.json` (relative to the working directory). We clear
that file at the start of every test so a stale override from a prior test
never silently flips a later test's `ai_api_key` from "" to "sk-test".
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_override_file():
    override_path = Path("data/settings_override.json")
    if override_path.exists():
        override_path.unlink()
    yield
    # Do not delete on teardown: PUT /api/settings mid-test should still be
    # observable by the same test's subsequent GET.
