class Target:
    def __init__(self, x: float, y: float, timestamp: float):
        """
        Normalized target position

        x, y: range [-1, 1]
        timestamp: seconds (float)
        """
        self.x = x
        self.y = y
        self.timestamp = timestamp

    def __repr__(self):
        return f"Target(x={self.x:.3f}, y={self.y:.3f}, t={self.timestamp:.3f})"