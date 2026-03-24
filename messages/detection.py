class Detection:
    def __init__(self, x1, y1, x2, y2, confidence, class_id, timestamp):
        """
        Bounding box in pixel coordinates
        """
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.confidence = confidence
        self.class_id = class_id
        self.timestamp = timestamp

    def center(self):
        cx = (self.x1 + self.x2) / 2
        cy = (self.y1 + self.y2) / 2
        return cx, cy

    def __repr__(self):
        return f"Detection(conf={self.confidence:.2f}, cls={self.class_id})"