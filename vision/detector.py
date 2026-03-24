from ultralytics import YOLO
from messages.detection import Detection
from utils.time_utils import now
import threading


class Detector:
    def __init__(self, model_path, conf_threshold=0.5, imgsz=320):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz

        self.latest_frame = None
        self.latest_detections = []

        self.lock = threading.Lock()

        # Start background thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            if self.latest_frame is None:
                continue

            frame = self.latest_frame.copy()

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
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    class_id = int(box.cls[0])

                    detections.append(
                        Detection(x1, y1, x2, y2, conf, class_id, now())
                    )

            with self.lock:
                self.latest_detections = detections

    def detect(self, frame):
        """
        Non-blocking detection
        """

        # Update frame for background thread
        self.latest_frame = frame

        # Return latest detections (instant)
        with self.lock:
            return self.latest_detections.copy()