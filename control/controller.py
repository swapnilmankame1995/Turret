from messages.command import Command
from utils.time_utils import now


class Controller:
    def __init__(self, pid_pan, pid_tilt):
        self.pid_pan = pid_pan
        self.pid_tilt = pid_tilt

    def update(self, target, dt):
        """
        target: Target object
        dt: time delta
        """

        error_x = target.x
        error_y = target.y

        pan = self.pid_pan.update(error_x, dt)
        tilt = self.pid_tilt.update(error_y, dt)

        return Command(pan, tilt, now())