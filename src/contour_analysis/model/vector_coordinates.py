from pydantic import BaseModel


class VectorCoordinates(BaseModel):
    vector_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    round_id: str
