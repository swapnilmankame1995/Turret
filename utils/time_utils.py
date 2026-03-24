import time

def now():
    return time.time()


class DeltaTimer:
    def __init__(self):
        self.last_time = None

    def dt(self):
        current = now()

        if self.last_time is None:
            self.last_time = current
            return 0.0

        dt = current - self.last_time
        self.last_time = current
        return dt