from ultralytics import YOLO
from multiprocessing import Process, Queue


class YOLOProcess:
    def __init__(self, model_path, conf=0.5, imgsz=320):
        self.input_q = Queue(maxsize=1)
        self.output_q = Queue(maxsize=1)

        self.process = Process(
            target=self._run,
            args=(model_path, conf, imgsz),
            daemon=True
        )
        self.process.start()

    def _run(self, model_path, conf, imgsz):
        model = YOLO(model_path)

        while True:
            frame = self.input_q.get()

            results = model.predict(
                frame,
                device="cuda",
                imgsz=imgsz,
                conf=conf,
                verbose=False
            )

            boxes = []

            for r in results:
                if r.boxes is None:
                    continue

                for b in r.boxes:
                    x1, y1, x2, y2 = map(int, b.xyxy[0])
                    boxes.append((x1, y1, x2, y2))

            if not self.output_q.full():
                self.output_q.put(boxes)

    def send(self, frame):
        if not self.input_q.full():
            self.input_q.put(frame)

    def get(self):
        if not self.output_q.empty():
            return self.output_q.get()
        return []
