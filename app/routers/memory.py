"""Memory routes — view, edit, delete facts from Memori."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryUpdateBody(BaseModel):
    content: str


class WipeBody(BaseModel):
    confirm: str


@router.get("")
def get_memories():
    service = MemoryService()
    return service.get_facts_grouped()


@router.put("/{fact_id}")
def update_memory(fact_id: int, body: MemoryUpdateBody):
    service = MemoryService()
    fact = service.update_fact(fact_id, body.content)
    if not fact:
        raise HTTPException(status_code=404, detail="Memory fact not found")
    return fact


@router.delete("/{fact_id}", status_code=204)
def delete_memory(fact_id: int):
    service = MemoryService()
    if not service.delete_fact(fact_id):
        raise HTTPException(status_code=404, detail="Memory fact not found")


@router.post("/wipe", status_code=204)
def wipe_memory(body: WipeBody):
    service = MemoryService()
    if not service.wipe_all(body.confirm):
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation. Send {'confirm': 'DELETE_ALL'}",
        )
