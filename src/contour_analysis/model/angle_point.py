from typing import Optional
from pydantic import BaseModel

class Point(BaseModel):
    x: float
    y: float
    id: str
    
class AnglePoint(Point):
    angle: float
    line1: Optional[str] = None
    line2: Optional[str] = None
    
class EndPoint(Point):
    line: str