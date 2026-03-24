import threading


class VisionThread:
    def __init__(self, vision_node):
        self.vision = vision_node

        self.frame = None
        self.target = None
        self.detection = None

        self.lock = threading.Lock()

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            if self.frame is None:
                continue

            frame = self.frame.copy()

            target, detection = self.vision.process(frame)

            with self.lock:
                self.target = target
                self.detection = detection

    def update_frame(self, frame):
        self.frame = frame

    def get_output(self):
        with self.lock:
            return self.target, self.detection
v