from dataclasses import dataclass


@dataclass
class DLQModel:
    source: str
    error: dict
    value: dict
