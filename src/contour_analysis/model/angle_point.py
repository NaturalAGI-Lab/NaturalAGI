class AnglePoint:
    def __init__(self, x: float, y: float, id: int):
        self.x: float = x
        self.y: float = y
        self.id: int = id

    def __str__(self):
        return f"AnglePoint(x={self.x}, y={self.y}, id={self.id})"