# backend/tests/test_e2e_onsite_welcome.py
"""§三.3 §八-6 验收：verify.passed 必须驱动 LED 显示姓名 + TTS 朗读欢迎词。

TTS 在 build_app 中可能装到 RealTTSAdapter（带音频设备），Mock 不可注入；改为通过
/api/work-logs?module=tts 验证 OnsiteWelcomeService 的 _publish_worklog 副作用。
LED 始终 MockLEDAdapter（main.py L64），可直接读 displayed 列表。
"""
from __future__ import annotations
import time
from datetime import date
import pandas as pd
from fastapi.testclient import TestClient
from app.adapters.led.mock import MockLEDAdapter
from app.core.config import Settings
from app.main import build_app


def _wait(pred, t=5.0, s=0.1):
    e = time.monotonic() + t
    while time.monotonic() < e:
        if pred(): return True
        time.sleep(s)
    return pred()


def test_e2e_passed_drives_led_and_tts(tmp_path):
    today = str(date.today())
    xlsx = tmp_path / "v.xlsx"
    cols = ["来访日期","计划场次时间","姓名","手机号","国籍","身份证号","性别","单位","身份"]
    vals = [[today, f"{today} 10:00", "张三", "13800000000", "中国", "110000000000000000", "男", "AITIC", "企业领导"]]
    pd.DataFrame(vals, columns=cols).to_excel(xlsx, index=False)
    app = build_app(Settings(database_url=f"sqlite:///{tmp_path}/app.db", excel_watch_dir=str(tmp_path/"incoming")))
    led: MockLEDAdapter = app.state.adapters["led"]
    with TestClient(app) as c, open(xlsx, "rb") as f:
        r = c.post("/api/import/preview", files={"file": ("v.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200, r.text
        r = c.post("/api/import/commit", json={"preview_id": r.json()["preview_id"]})
        assert r.status_code == 200, r.text
        vid = r.json()["visit_ids"][0]
        # §3.2 写卡是手动动作，先调用 /api/cards/write
        r = c.post("/api/cards/write", json={"visit_ids": [vid]})
        assert r.status_code == 200, r.text
        assert _wait(lambda: any(x["visit_id"] == vid for x in c.get("/api/cards/write-log").json()), 10.0), "no card write"
        uid = next(x["card_uid"] for x in c.get("/api/cards/write-log").json() if x["visit_id"] == vid)
        v = c.get(f"/api/visits/{vid}").json()
        s = c.post("/api/debug/simulate-card-read", json={"card_uid": uid, "raw_payload": {"visit_id": vid, "name": v["name"], "visit_date": v["visit_date"]}})
        assert s.status_code == 200, s.text
        assert _wait(lambda: led.displayed, 5.0), f"LED never displayed: {led.displayed}"
        # LED 收到姓名（§三.3）+ TTS 走 work_log 副作用（module=tts action=speak）
        assert led.displayed[-1].name == v["name"]
        assert _wait(lambda: any(l["action"] == "speak" and l["module"] == "tts"
                                  and f"visit_id={vid}" in l["detail"]
                                  for l in c.get("/api/work-logs", params={"module": "tts"}).json()), 5.0), "TTS work_log never recorded"
