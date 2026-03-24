class Command:
    def __init__(self, pan: float, tilt: float, timestamp: float):
        """
        pan, tilt: normalized velocity [-1, 1]
        timestamp: seconds
        """
        self.pan = pan
        self.tilt = tilt
        self.timestamp = timestamp

    def __repr__(self):
        return f"Command(pan={self.pan:.3f}, tilt={self.tilt:.3f}, t={self.timestamp:.3f})"