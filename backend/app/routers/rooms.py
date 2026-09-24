from fastapi import APIRouter, HTTPException
from app.schemas.openings import OpeningCreate
from app.services.paint_service import PaintService
router = APIRouter()
@router.get("/rooms")
def list_rooms():
    with PaintService() as s: return {"items": s.list_rooms()}
@router.get("/rooms/{room_id}")
def room_detail(room_id: int):
    with PaintService() as s:
        d = s.room_detail(room_id)
        if not d: raise HTTPException(404)
        return d
@router.post("/rooms/{room_id}/openings")
def add_opening(room_id: int, body: OpeningCreate):
    with PaintService() as s:
        d = s.add_opening(room_id, body.kind, body.w, body.h)
        if not d: raise HTTPException(404)
        return d
@router.delete("/openings/{opening_id}")
def delete_opening(opening_id: int):
    with PaintService() as s:
        d = s.delete_opening(opening_id)
        if not d: raise HTTPException(404)
        return d
