"""
Turret PID Controller
======================
A clean, tunable dual-axis PID for turret motor control.

Designed to consume (x_err, y_err) from tracker_v1.1 and output
(pan_cmd, tilt_cmd) in range [-1, 1] — ready for a motor driver.

Tuning guide:
  Start with I=0, D=0. Raise P until the turret oscillates, then back off 30%.
  Add small D (~10% of P) to damp overshoot on fast targets.
  Add tiny I (~1-5% of P) only if the turret consistently stops slightly off-center.

Anti-windup:
  Integral is clamped to I_CLAMP. This prevents the integrator from accumulating
  during long periods of error (e.g. target lost) and then slamming the motor
  when the target reappears.

Output clamping:
  Final output is always clamped to [-1, 1]. Map this to your motor driver's
  speed/direction range (e.g. PWM 0-255, or RPM).
"""

import time


class PIDAxis:
    """Single-axis PID controller."""

    def __init__(self, kp, ki, kd, i_clamp=0.3, output_clamp=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.i_clamp     = i_clamp      # Max absolute value of integral term
        self.output_clamp = output_clamp

        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None

    def update(self, error: float) -> float:
        """
        Feed in current error, get back a clamped motor command [-1, 1].
        Call once per frame.
        """
        now = time.monotonic()

        if self._prev_time is None:
            dt = 0.033          # Assume ~30fps on first call
        else:
            dt = now - self._prev_time
            dt = max(dt, 1e-6)  # Guard against zero dt

        self._prev_time = now

        # ── P term ──────────────────────────────────────────
        p = self.kp * error

        # ── I term (with anti-windup clamp) ─────────────────
        self._integral += error * dt
        self._integral  = max(-self.i_clamp,
                          min( self.i_clamp, self._integral))
        i = self.ki * self._integral

        # ── D term (on error, not on measurement) ────────────
        # Using error derivative directly is fine here because
        # the EMA in the tracker already smoothed the input.
        d_error = (error - self._prev_error) / dt
        d = self.kd * d_error
        self._prev_error = error

        # ── Sum and clamp ────────────────────────────────────
        output = p + i + d
        output = max(-self.output_clamp,
                 min( self.output_clamp, output))

        return output, p, i, d     # Return components for HUD debug display

    def reset(self):
        """Call when target is lost to prevent integral windup carryover."""
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None


class TurretPID:
    """
    Dual-axis PID — pan (x) and tilt (y) share the same gains
    since the turret mechanics are symmetric.

    If your pan and tilt motors have different inertia/gearing,
    create separate PIDAxis instances with different gains.
    """

    def __init__(self, kp=0.6, ki=0.01, kd=0.08):
        self.pan  = PIDAxis(kp, ki, kd)
        self.tilt = PIDAxis(kp, ki, kd)

    def update(self, x_err: float, y_err: float):
        """
        Returns:
          pan_cmd  : float [-1, 1] — positive = rotate right
          tilt_cmd : float [-1, 1] — positive = tilt up
          debug    : dict  — P/I/D components for display
        """
        pan_cmd,  p_x, i_x, d_x = self.pan.update(x_err)
        tilt_cmd, p_y, i_y, d_y = self.tilt.update(y_err)

        debug = {
            "pan":  {"p": p_x, "i": i_x, "d": d_x, "out": pan_cmd},
            "tilt": {"p": p_y, "i": i_y, "d": d_y, "out": tilt_cmd},
        }
        return pan_cmd, tilt_cmd, debug

    def reset(self):
        self.pan.reset()
        self.tilt.reset()

    def set_gains(self, kp, ki, kd):
        """Hot-swap gains at runtime — useful for tuning."""
        for axis in (self.pan, self.tilt):
            axis.kp = kp
            axis.ki = ki
            axis.kd = kd
