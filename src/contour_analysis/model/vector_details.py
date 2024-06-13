class VectorDetails:
    def __init__(self, id: str, x1: float, y1: float, x2: float, y2: float, length: float):
        self.id: str = id
        self.x1: float = x1
        self.y1: float = y1
        self.x2: float = x2
        self.y2: float = y2
        self.length: float = length

    def __str__(self):
        return (f"VectorDetails(uuid={self.id}, x1={self.x1}, y1={self.y1}, x2={self.x2}, y2={self.y2}), "
                f"length={self.length})")
