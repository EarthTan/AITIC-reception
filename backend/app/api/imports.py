# backend/app/api/imports.py
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import get_services
from app.models.visit import EntrySource
from app.schemas.visit import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
    ImportPreviewRow,
)

router = APIRouter(prefix="/api/import", tags=["import"])

PENDING_IMPORT_DIR = Path("data/pending_imports")


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile, services: dict = Depends(get_services)
) -> ImportPreviewResponse:
    PENDING_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    preview_id = str(uuid.uuid4())
    dest = PENDING_IMPORT_DIR / f"{preview_id}.xlsx"
    dest.write_bytes(await file.read())

    registration_service = services["registration"]
    try:
        parsed_rows = registration_service.parse_excel(str(dest))
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows = [
        ImportPreviewRow(
            row_number=row.row_number,
            data=row.data,
            errors=row.errors,
            is_valid=row.is_valid,
        )
        for row in parsed_rows
    ]
    return ImportPreviewResponse(
        preview_id=preview_id,
        rows=rows,
        valid_count=sum(1 for row in rows if row.is_valid),
        invalid_count=sum(1 for row in rows if not row.is_valid),
    )


@router.post("/commit", response_model=ImportCommitResponse)
async def commit_import(
    body: ImportCommitRequest, services: dict = Depends(get_services)
) -> ImportCommitResponse:
    dest = PENDING_IMPORT_DIR / f"{body.preview_id}.xlsx"
    if not dest.exists():
        raise HTTPException(
            status_code=404, detail="预览记录不存在或已过期，请重新上传"
        )

    registration_service = services["registration"]
    try:
        import_batch_id, visit_ids = await registration_service.import_file(
            str(dest), EntrySource.MANUAL
        )
    finally:
        # Always clean up the staged file, even on partial failure inside import_file
        dest.unlink(missing_ok=True)
    return ImportCommitResponse(import_batch_id=import_batch_id, visit_ids=visit_ids)
