from dataclasses import dataclass
from enum import Enum

class Reason(Enum):
    FIRST_POINT = "First point"
    FIRST_LINE = "First Line"

@dataclass(frozen=True)
class CriticalPoint:
    uuid: str
    image_id: str
    reason: Reason
    connectedVerts = {}