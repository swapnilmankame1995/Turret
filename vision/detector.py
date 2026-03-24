from vision.yolo_process import YOLOProcess
from messages.detection import Detection
from utils.time_utils import now


class Detector:
    def __init__(self, model_path, conf_threshold=0.5):
        self.yolo = YOLOProcess(model_path, conf_threshold)

    def detect(self, frame):
        self.yolo.send(frame)

        boxes = self.yolo.get()

        detections = []

        for (x1, y1, x2, y2) in boxes:
            detections.append(
                Detection(x1, y1, x2, y2, 1.0, 0, now())
            )

        return detections
