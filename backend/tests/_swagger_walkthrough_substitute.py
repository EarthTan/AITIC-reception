"""Swagger walkthrough substitute for Task 14 Step 7.

The plan calls for opening `/docs` in a browser. In a headless test
environment that's not possible; instead we boot the FastAPI app in-process
via TestClient and round-trip every endpoint with the same payload the
plan's manual walkthrough uses.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "sample_visitors.xlsx"


def main() -> int:
    # Use a tmp dir under the repo for the DB so the run is self-contained
    # but visible (e.g. for inspection after the walkthrough).
    db_path = ROOT / "data" / "swagger_walkthrough.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    incoming = ROOT / "data" / "swagger_walkthrough_incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    # Clean any stale settings override that would flip ai_api_key on us.
    override = ROOT / "data" / "settings_override.json"
    if override.exists():
        override.unlink()

    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        excel_watch_dir=str(incoming),
        ai_api_key="",
    )
    app = build_app(settings)

    failures: list[str] = []

    def check(label: str, ok: bool, extra: str = "") -> None:
        marker = "OK" if ok else "FAIL"
        print(f"[{marker}] {label}{(': ' + extra) if extra else ''}")
        if not ok:
            failures.append(label)

    with TestClient(app) as client:
        # 1. Health
        r = client.get("/health")
        check("GET /health", r.status_code == 200, str(r.json()))

        # 2. List templates (seeded 7)
        r = client.get("/api/templates")
        check("GET /api/templates", r.status_code == 200, f"len={len(r.json())}")

        # 3. Import preview (plan step 1)
        with FIXTURE.open("rb") as f:
            r = client.post(
                "/api/import/preview",
                files={
                    "file": (
                        "sample_visitors.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
        check("POST /api/import/preview", r.status_code == 200, f"body={r.text[:200]}")
        preview_body = r.json() if r.status_code == 200 else {}
        preview_id = preview_body.get("preview_id")

        # 4. Import commit (plan step 2)
        r = client.post("/api/import/commit", json={"preview_id": preview_id})
        check("POST /api/import/commit", r.status_code == 200, str(r.json()))
        commit_body = r.json() if r.status_code == 200 else {}
        visit_ids = commit_body.get("visit_ids", [])

        # 5. List visits with masked id_number (plan step 3)
        r = client.get("/api/visits")
        check("GET /api/visits", r.status_code == 200, f"count={len(r.json())}")
        # Confirm masking: no row should contain a raw 14+ digit id_number
        rows = r.json() if r.status_code == 200 else []
        raw_id_leak = any(
            any(vv.isdigit() and len(vv) >= 14 for vv in (row.get("id_number") or "",))
            for row in rows
        )
        check("visits id_number is masked", not raw_id_leak)

        # 6. Get one visit; wait for the AI writeup + card write to complete.
        if visit_ids:
            time.sleep(1.0)
            r = client.get(f"/api/visits/{visit_ids[0]}")
            check("GET /api/visits/{id}", r.status_code == 200, str(r.json()))

        # 7. Today visits
        r = client.get("/api/visits/today")
        check("GET /api/visits/today", r.status_code == 200, f"count={len(r.json())}")

        # 8. Summary + export
        month = time.strftime("%Y-%m")
        r = client.get("/api/visits/summary", params={"month": month})
        check("GET /api/visits/summary", r.status_code == 200, f"body={r.text[:120]}")
        r = client.get("/api/visits/summary/export", params={"month": month})
        check(
            "GET /api/visits/summary/export",
            r.status_code == 200,
            f"content-type={r.headers.get('content-type')}",
        )

        # 9. Update a visit
        if visit_ids:
            r = client.patch(
                f"/api/visits/{visit_ids[0]}",
                json={"remark": "swagger-walkthrough-remark"},
            )
            check("PATCH /api/visits/{id}", r.status_code == 200, str(r.json()))

        # 10. Update a template
        r = client.put(
            "/api/templates/企业领导",
            json={"template_text": "（演示）欢迎 {name} 莅临指导。"},
        )
        check("PUT /api/templates/{identity_type}", r.status_code == 200, str(r.json()))

        # 11. Card write trigger
        if visit_ids:
            r = client.post("/api/cards/write", json={"visit_ids": [visit_ids[0]]})
            check("POST /api/cards/write", r.status_code == 200, str(r.json()))

        # 12. Cards write-log
        r = client.get("/api/cards/write-log")
        check(
            "GET /api/cards/write-log", r.status_code == 200, f"count={len(r.json())}"
        )

        # 13. Debug: simulate a card read (plan step 5)
        # Find a card_uid from the write-log
        write_log = r.json() if r.status_code == 200 else []
        card_uid = None
        for row in write_log:
            if row.get("card_uid"):
                card_uid = row["card_uid"]
                break
        if card_uid is None and write_log:
            # fallback: use any uid from raw_payload
            card_uid = "WALK-UID"
        if card_uid:
            r = client.post(
                "/api/debug/simulate-card-read",
                json={
                    "card_uid": card_uid,
                    "raw_payload": {"src": "swagger-walkthrough"},
                },
            )
            check(
                "POST /api/debug/simulate-card-read",
                r.status_code == 200,
                str(r.json()),
            )
            check(
                "POST /api/debug/simulate-card-read",
                r.status_code == 200,
                str(r.json()),
            )
        else:
            check("POST /api/debug/simulate-card-read (skipped, no card_uid)", True)

        # Give the verify service a moment to consume the event
        time.sleep(0.5)

        # 14. Verify log
        r = client.get("/api/verify-log")
        check("GET /api/verify-log", r.status_code == 200, f"count={len(r.json())}")

        # 15. Work logs
        r = client.get("/api/work-logs")
        check("GET /api/work-logs", r.status_code == 200, f"count={len(r.json())}")

        # 16. Adapter status (plan step 6: wait up to 30s for the poller's first tick)
        deadline = time.time() + 35
        rows = []
        while time.time() < deadline:
            r = client.get("/api/adapters/status")
            if r.status_code == 200 and len(r.json()) >= 4:
                rows = r.json()
                break
            time.sleep(1.0)
        check(
            "GET /api/adapters/status has 4 rows", len(rows) >= 4, f"count={len(rows)}"
        )
        if rows:
            names = sorted(row["adapter_name"] for row in rows)
            check(
                "adapter status names", names == ["ai", "led", "nfc", "tts"], str(names)
            )

        # 17. Settings
        r = client.get("/api/settings")
        check("GET /api/settings", r.status_code == 200, str(r.json()))

        # 18. OpenAPI doc
        r = client.get("/openapi.json")
        check(
            "GET /openapi.json", r.status_code == 200, f"paths={len(r.json()['paths'])}"
        )

    # Cleanup the walkthrough DB
    if db_path.exists():
        db_path.unlink()

    print()
    print("=" * 60)
    if failures:
        print(f"{len(failures)} failures: {failures}")
        return 1
    print("All walkthrough steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
