"""Regression: 写卡必须手动触发。

TARGET §2.2 / §3.2 要求值班人员"触发写卡"——welcome.generated 不再自动驱动 CardService。
本测试断言：导入 Excel 后 visit 停在 welcome_ready，状态不会自动跳到 card_written；
只有手动调用 CardService.write_card_for_visit 后才转 card_written。
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import build_app


def _make_xlsx() -> bytes:
    df = pd.DataFrame(
        [
            {
                "来访日期": "2026-07-07",
                "计划场次时间": "2026-07-07 09:00",
                "姓名": "测试人",
                "手机号": "13800000099",
                "国籍": "中国",
                "身份证号": "110101199001010099",
                "性别": "男",
                "单位": "测试单位",
                "身份": "企业员工",
            }
        ]
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def test_import_does_not_auto_write_card():
    """导入 Excel 后，visit 应停在 welcome_ready，不会自动 card_written。"""
    app = build_app(Settings())
    with TestClient(app) as client:
        # 1. 预览（导入）
        resp = client.post(
            "/api/import/preview",
            files={
                "file": (
                    "t.xlsx",
                    _make_xlsx(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert resp.status_code == 200
        preview_id = resp.json()["preview_id"]

        # 2. 提交
        resp = client.post("/api/import/commit", json={"preview_id": preview_id})
        assert resp.status_code == 200
        visit_id = resp.json()["visit_ids"][0]

        # 3. 等 AI 异步处理完毕（welcome.generated 发完）
        import time

        time.sleep(0.5)

        # 4. 断言 visit 停在 welcome_ready，未自动写卡
        v = client.get(f"/api/visits/{visit_id}").json()
        assert v["status"] == "welcome_ready", (
            f"expected welcome_ready after import (manual §3.2), got {v['status']!r}"
        )

        # 5. 断言 CardManagementPage filter 能找到这条
        visits = client.get("/api/visits").json()
        writable = [x for x in visits if x["status"] == "welcome_ready"]
        assert any(x["id"] == visit_id for x in writable), (
            "新导入访客应出现在待写卡列表中"
        )

        # 6. 手动触发写卡
        resp = client.post("/api/cards/write", json={"visit_ids": [visit_id]})
        assert resp.status_code == 200
        assert resp.json()[0]["status"] == "success"

        # 7. 状态变为 card_written
        v = client.get(f"/api/visits/{visit_id}").json()
        assert v["status"] == "card_written", (
            f"expected card_written after manual write, got {v['status']!r}"
        )
