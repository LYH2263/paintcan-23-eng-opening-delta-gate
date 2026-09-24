from pydantic import BaseModel
class OpeningCreate(BaseModel):
    kind: str = "window"
    w: float
    h: float
