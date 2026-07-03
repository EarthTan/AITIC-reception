# backend/app/services/registration_service.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from app.core.event_bus import EventBus
from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus

REQUIRED_COLUMNS = [
    "来访日期",
    "计划场次时间",
    "姓名",
    "手机号",
    "国籍",
    "身份证号",
    "性别",
    "单位",
    "身份",
]
MANDATORY_FIELDS = ["来访日期", "计划场次时间", "姓名", "身份"]
VALID_IDENTITIES = {member.value for member in IdentityType}


@dataclass
class ParsedRow:
    row_number: int
    data: dict
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class RegistrationService:
    def __init__(self, session_factory, event_bus: EventBus) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus

    def parse_excel(self, file_path: str) -> list[ParsedRow]:
        frame = pd.read_excel(file_path, dtype=str)
        missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
        if missing:
            raise ValueError(f"表头缺少必填列: {missing}")

        parsed_rows: list[ParsedRow] = []
        for offset, row in enumerate(frame.to_dict(orient="records")):
            row_number = offset + 2  # +2: 1-indexed rows, plus header row
            errors: list[str] = []
            for field_name in MANDATORY_FIELDS:
                value = row.get(field_name)
                if (
                    value is None
                    or (isinstance(value, float) and pd.isna(value))
                    or str(value).strip() == ""
                ):
                    errors.append(f"{field_name}不能为空")
            identity = row.get("身份")
            if identity and identity not in VALID_IDENTITIES:
                errors.append(f"身份取值非法: {identity}")
            parsed_rows.append(
                ParsedRow(row_number=row_number, data=row, errors=errors)
            )
        return parsed_rows

    async def import_file(
        self, file_path: str, entry_source: EntrySource
    ) -> tuple[str, list[int]]:
        parsed_rows = self.parse_excel(file_path)
        valid_rows = [row for row in parsed_rows if row.is_valid]
        invalid_rows = [row for row in parsed_rows if not row.is_valid]

        import_batch_id = str(uuid.uuid4())
        visit_ids: list[int] = []
        with self._session_factory() as session:
            for row in valid_rows:
                visit = Visit(
                    visit_date=_parse_date(row.data["来访日期"]),
                    session_time=_parse_datetime(row.data["计划场次时间"]),
                    name=row.data["姓名"],
                    phone=row.data.get("手机号"),
                    nationality=row.data.get("国籍"),
                    id_number=row.data.get("身份证号"),
                    gender=row.data.get("性别"),
                    organization=row.data.get("单位"),
                    identity_type=IdentityType(row.data["身份"]),
                    entry_source=entry_source,
                    import_batch_id=import_batch_id,
                    status=VisitStatus.PENDING,
                )
                session.add(visit)
                session.flush()
                visit_ids.append(visit.id)
            session.commit()

        if invalid_rows:
            detail = "; ".join(
                f"第{row.row_number}行: {','.join(row.errors)}" for row in invalid_rows
            )
            await self._event_bus.publish(
                "work_log.append",
                {
                    "module": "registration",
                    "action": "import_file",
                    "status": "warning",
                    "detail": f"{len(invalid_rows)} 行校验失败: {detail}",
                },
            )

        if visit_ids:
            await self._event_bus.publish(
                "visit.imported",
                {"visit_ids": visit_ids, "import_batch_id": import_batch_id},
            )
            for visit_id in visit_ids:
                await self._event_bus.publish(
                    "welcome.requested", {"visit_id": visit_id}
                )
            await self._event_bus.publish(
                "work_log.append",
                {
                    "module": "registration",
                    "action": "import_file",
                    "status": "success",
                    "detail": f"批次{import_batch_id}导入{len(visit_ids)}条记录",
                },
            )

        return import_batch_id, visit_ids

    async def handle_excel_detected(self, payload: dict) -> None:
        await self.import_file(payload["file_path"], EntrySource.AUTO)


def _parse_date(value: str) -> date:
    return pd.to_datetime(value).date()


def _parse_datetime(value: str) -> datetime:
    return pd.to_datetime(value).to_pydatetime()
