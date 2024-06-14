from pydantic import BaseModel


class AnglePointAnalysisDetails(BaseModel):
    id: str
    image_id: str
    round_id: str
    x: float
    y: float
    angle: float
    is_direction_change: bool
    is_quadrant_change: bool
