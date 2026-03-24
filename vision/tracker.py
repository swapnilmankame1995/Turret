import cv2
from messages.target import Target
from utils.time_utils import now


class Tracker:
    def __init__(self):
        self.tracker = None
        self.active = False

    def init(self, frame, detection):
        x1, y1, x2, y2 = detection.x1, detection.y1, detection.x2, detection.y2
        w = x2 - x1
        h = y2 - y1

        try:
            self.tracker = cv2.legacy.TrackerKCF_create()
        except:
            self.tracker = cv2.TrackerKCF_create()

        self.tracker.init(frame, (x1, y1, w, h))
        self.active = True

    def update(self, frame):
        if not self.active:
            return None

        success, box = self.tracker.update(frame)

        if not success:
            self.active = False
            return None

        x, y, w, h = box
        cx = x + w / 2
        cy = y + h / 2

        h_frame, w_frame, _ = frame.shape

        # Normalize to [-1, 1]
        norm_x = (cx - w_frame / 2) / (w_frame / 2)
        norm_y = (cy - h_frame / 2) / (h_frame / 2)

        return Target(norm_x, norm_y, now())
