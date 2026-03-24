from ultralytics import YOLO
from messages.detection import Detection
from utils.time_utils import now


class Detector:
    def __init__(self, model_path, conf_threshold=0.5, imgsz=320):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz

        # Run YOLO less frequently (VERY IMPORTANT)
        self.frame_count = 0
        self.detect_every = 3  # run detection every N frames

    def detect(self, frame):
        """
        Returns list of Detection objects
        """

        self.frame_count += 1

        # --- Throttle detection ---
        if self.frame_count % self.detect_every != 0:
            return []

        # --- Run YOLO ---
        results = self.model.predict(
            frame,
            device="cuda",
            imgsz=self.imgsz,
            conf=self.conf_threshold,
            verbose=False
        )

        detections = []

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                conf = float(box.conf[0])

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])

                detections.append(
                    Detection(x1, y1, x2, y2, conf, class_id, now())
                )

        return detections