from pydantic import BaseModel


class VectorValue(BaseModel):
    x: float
    y: float
