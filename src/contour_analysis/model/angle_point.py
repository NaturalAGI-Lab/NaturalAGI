class AnglePoint:
    def __init__(self, x: float, y: float, id: int, angle: float, line1: str, line2: str):
        self.x: float = x
        self.y: float = y
        self.id: int = id
        self.angle: float = angle
        self.line1: str = line1
        self.line2: str = line2

    def __str__(self):
        return (f"AnglePoint(x={self.x}, y={self.y}, id={self.id}, angle={self.angle}, line1={self.line1}, "
                f"line2={self.line2})")
