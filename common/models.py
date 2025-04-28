from enum import Enum
from pydantic import BaseModel

class DLQModel(BaseModel):
    source: str
    error: dict
    value: dict
    
class ContourType(Enum):
    CLOSED = "Closed"
    OPEN = "Open"
    
class ContourDevelopment(Enum):
    MONOTONIC = "Monotonic"
    NON_MONOTONIC = "Non-monotonic"
    UNKNOWN = "Unknown"
