from ultralytics import YOLO
from multiprocessing import Process, SimpleQueue

class YOLOProcess:
    def __init__(self, model_path, conf=0.5, imgsz=320):


        self.input_q = SimpleQueue()
        self.output_q = SimpleQueue()   

        self.process = Process(
            target=self._run,
            args=(model_path, conf, imgsz),
            daemon=True
        )
        self.process.start()

    def _run(self, model_path, conf, imgsz):
        model = YOLO(model_path)

        while True:
            if self.input_q.empty():
              continue

            frame = None


            while True:
                try:
                    frame = self.input_q.get_nowait()
                except:
                    break

            if frame is None:
                continue

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


            try:
                while True:
                    self.output_q.get_nowait()
            except:
                pass

            self.output_q.put(boxes)


    def send(self, frame):
        try:
            while True:
                self.input_q.get_nowait()
        except:
            pass

        self.input_q.put(frame)

    def get(self):


        boxes = None

        while True:
            try:
                boxes = self.output_q.get_nowait()
            except:
                break

        return boxes if boxes is not None else []
