import io

import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.event_bus import EventBus
from app.main import build_app


def _make_xlsx() -> bytes:
    df = pd.DataFrame(
        [
            {
                "来访日期": "2026-07-07",
                "计划场次时间": "2026-07-07 09:00",
                "姓名": "张三",
                "手机号": "13800000000",
                "国籍": "中国",
                "身份证号": "110101199001010011",
                "性别": "男",
                "单位": "某单位",
                "身份": "企业员工",
            }
        ]
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def test_import_preview_masks_id_number():
    app = build_app(Settings())
    with TestClient(app) as client:
        resp = client.post(
            "/api/import/preview",
            files={
                "file": (
                    "test.xlsx",
                    _make_xlsx(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    rows = body["rows"]
    assert rows[0]["data"]["身份证号"] != "110101199001010011"
    # mask 形如 110*******0011（3 + 7 asterisks + 4，对应 mask_id_number 契约）
    assert "*******" in rows[0]["data"]["身份证号"]
