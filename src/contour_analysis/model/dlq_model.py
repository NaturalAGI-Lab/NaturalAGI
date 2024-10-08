# Pedantic DLQ model for the Kafka topic

from pydantic import BaseModel

class DLQModel(BaseModel):
    source: str
    message: str
    value: dict
    