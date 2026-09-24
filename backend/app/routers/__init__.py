from fastapi import APIRouter
from app.routers import dashboard, estimate, history, openings, rooms, settings
api = APIRouter(prefix="/api")
for r in (dashboard, rooms, estimate, history, settings, openings): api.include_router(r.router)
