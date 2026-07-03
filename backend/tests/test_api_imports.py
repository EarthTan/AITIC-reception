# backend/tests/test_api_imports.py
from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def _sample_excel_bytes() -> bytes:
    buffer = BytesIO()
    pd.DataFrame(
        [
            {
                "来访日期": "2026-07-06",
                "计划场次时间": "2026-07-06 10:00",
                "姓名": "张三",
                "手机号": "13800000000",
                "国籍": "中国",
                "身份证号": "110101199001010000",
                "性别": "男",
                "单位": "AITIC",
                "身份": "企业领导",
            },
            {
                "来访日期": "2026-07-06",
                "计划场次时间": "",  # missing mandatory field -> invalid row
                "姓名": "李四",
                "手机号": "13800000001",
                "国籍": "中国",
                "身份证号": "110101199001010001",
                "性别": "女",
                "单位": "AITIC",
                "身份": "企业员工",
            },
        ]
    ).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer.read()


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/app.db",
        excel_watch_dir=str(tmp_path / "incoming"),
    )
    return TestClient(build_app(settings))


def test_preview_then_commit_imports_only_valid_rows(tmp_path):
    with _client(tmp_path) as client:
        files = {
            "file": (
                "visitors.xlsx",
                _sample_excel_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        preview_response = client.post("/api/import/preview", files=files)
        assert preview_response.status_code == 200
        preview_body = preview_response.json()
        assert preview_body["valid_count"] == 1
        assert preview_body["invalid_count"] == 1

        commit_response = client.post(
            "/api/import/commit", json={"preview_id": preview_body["preview_id"]}
        )
        assert commit_response.status_code == 200
        commit_body = commit_response.json()
        assert len(commit_body["visit_ids"]) == 1


def test_commit_with_unknown_preview_id_returns_404(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/api/import/commit", json={"preview_id": "does-not-exist"}
        )
        assert response.status_code == 404
