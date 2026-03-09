"""Domain routes — CRUD for life domains."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.domain import DomainCreate, DomainUpdate, DomainResponse
from app.services.domain_service import DomainService

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("", response_model=list[DomainResponse])
def list_domains(include_archived: bool = False, db: Session = Depends(get_db)):
    service = DomainService(db)
    return service.list_domains(include_archived=include_archived)


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    service = DomainService(db)
    domain = service.get_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.post("", response_model=DomainResponse, status_code=201)
def create_domain(data: DomainCreate, db: Session = Depends(get_db)):
    service = DomainService(db)
    return service.create_domain(data)


@router.put("/{domain_id}", response_model=DomainResponse)
def update_domain(domain_id: int, data: DomainUpdate, db: Session = Depends(get_db)):
    service = DomainService(db)
    domain = service.update_domain(domain_id, data)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.delete("/{domain_id}", status_code=204)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    service = DomainService(db)
    if not service.delete_domain(domain_id):
        raise HTTPException(status_code=404, detail="Domain not found")
