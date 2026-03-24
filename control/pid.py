class PID:
    def __init__(self, kp, ki, kd, output_limit=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.integral = 0.0
        self.prev_error = 0.0

        self.output_limit = output_limit

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error, dt):
        if dt <= 0:
            return 0.0

        # Integral
        self.integral += error * dt

        # Derivative
        derivative = (error - self.prev_error) / dt

        # PID output
        output = (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )

        # Clamp output
        output = max(min(output, self.output_limit), -self.output_limit)

        self.prev_error = error
        return output