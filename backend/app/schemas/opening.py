from pydantic import BaseModel, Field
class OpeningCreate(BaseModel):
    kind: str
    w: float = Field(gt=0)
    h: float = Field(gt=0)
