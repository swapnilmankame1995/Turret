class VisionNode:
    def __init__(self, detector, tracker):
        self.detector = detector
        self.tracker = tracker

    def process(self, frame):
        """
        Returns:
        (target, detection)
        """

        detection_used = None

        # --- If tracker active → use it ---
        if self.tracker.active:
            target = self.tracker.update(frame)
            if target is not None:
                return target, None

        # --- Else → run detection ---
        detections = self.detector.detect(frame)

        if len(detections) == 0:
            return None, None

        # Pick best detection
        best = max(detections, key=lambda d: d.confidence)

        # Initialize tracker
        self.tracker.init(frame, best)
        detection_used = best

        return None, detection_used