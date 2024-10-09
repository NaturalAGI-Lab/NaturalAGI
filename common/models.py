from pydantic import BaseModel

class DLQModel(BaseModel):
    source: str
    error: dict
    value: dict