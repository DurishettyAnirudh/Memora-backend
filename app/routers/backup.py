"""Backup routes — export, import, backup, wipe."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.services.backup_service import BackupService

import json

router = APIRouter(prefix="/api", tags=["backup"])


class WipeRequest(BaseModel):
    confirm: str


@router.get("/export")
def export_data(format: str = "json", db: Session = Depends(get_db)):
    service = BackupService(db)

    if format == "csv":
        csv_data = service.export_csv()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=memora_export.csv"},
        )

    data = service.export_json()
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=memora_export.json"},
    )


@router.post("/import")
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are accepted")

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    service = BackupService(db)
    return service.import_json(data)


@router.post("/backup")
def create_backup(db: Session = Depends(get_db)):
    service = BackupService(db)
    return service.create_backup()


@router.post("/wipe", status_code=204)
def wipe_data(body: WipeRequest, db: Session = Depends(get_db)):
    service = BackupService(db)
    if not service.wipe_all_data(body.confirm):
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation. Send {'confirm': 'WIPE_ALL_DATA'}",
        )
