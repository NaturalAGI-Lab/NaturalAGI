from pydantic import BaseModel


class AnglePoint(BaseModel):
    x: float
    y: float
    id: str
    angle: float
    line1: str
    line2: str
