from fastapi import APIRouter, HTTPException
from app.schemas.opening import OpeningCreate
from app.services.paint_service import PaintService
router = APIRouter()
@router.post("/rooms/{room_id}/openings", status_code=201)
def post_opening(room_id: int, body: OpeningCreate):
    with PaintService() as s:
        o = s.add_opening(room_id, body.kind, body.w, body.h)
        if not o: raise HTTPException(404)
        return o
@router.delete("/openings/{opening_id}")
def delete_opening(opening_id: int):
    with PaintService() as s:
        if not s.delete_opening(opening_id): raise HTTPException(404)
        return {"deleted": opening_id}
