"""
UGV Turret Targeting System - V1.1
====================================
Changes from V1:
  - Kalman measurement noise increased (trusts raw CSRT less, smooths more)
  - EMA filter on final error output (low-pass gate before motor signal)
  - Deadzone on error output (micro-vibration on still target -> exact 0.0)

Tuning guide (CONFIG section):
  - EMA_ALPHA  : 0.05 = very smooth, sluggish | 0.3 = more responsive, some jitter
                 Start at 0.12, tune from there
  - DEADZONE   : 0.01 kills micro-vibration on still target
                 Increase to 0.02 if still jittery

Controls:
  - Left-click  : lock onto target
  - Right-click : deselect
  - Q           : quit

Output:
  - x_err, y_err : smoothed + deadzoned, range [-1, 1], ready for PID
"""

import cv2
import numpy as np

# ── CONFIG ────────────────────────────────────────────────────────────────────

CAMERA_INDEX = 0       # Change if webcam isn't index 0
PATCH_SIZE = 80      # Tracking patch size around click point (px)
LOST_FRAME_LIMIT = 15      # Bad frames before lock drops

EMA_ALPHA = 0.12    # EMA smoothing — lower = smoother, more lag
DEADZONE = 0.01    # Error below this outputs 0.0 exactly

# ── KALMAN FILTER ─────────────────────────────────────────────────────────────


def create_kalman():
    """
    State  : (cx, cy, vx, vy)
    Measure: (cx, cy)

    Tuning vs V1:
      processNoiseCov     : kept low  — filter trusts its own motion model
      measurementNoiseCov : increased — filter trusts raw CSRT position less
      Net effect          : smoother output, slightly more lag on fast motion
                            (acceptable for turret; motors can't react to noise anyway)
    """
    kf = cv2.KalmanFilter(4, 2)

    kf.measurementMatrix = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0]
    ], dtype=np.float32)

    kf.transitionMatrix = np.array([
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01   # was 0.03
    kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 4.0    # was 0.5
    kf.errorCovPost = np.eye(4, dtype=np.float32)

    return kf


def kalman_update(kf, cx, cy):
    measurement = np.array([[np.float32(cx)], [np.float32(cy)]])
    kf.correct(measurement)
    predicted = kf.predict()
    return int(predicted[0].item()), int(predicted[1].item())


def kalman_predict_only(kf):
    predicted = kf.predict()
    return int(predicted[0].item()), int(predicted[1].item())

# ── SMOOTHING HELPERS ─────────────────────────────────────────────────────────


def ema(prev, new, alpha):
    """Exponential Moving Average — single-pole low-pass filter."""
    return alpha * new + (1.0 - alpha) * prev


def apply_deadzone(value, threshold):
    """Clamp small values to exactly 0.0 — kills micro-vibration on still target."""
    return 0.0 if abs(value) < threshold else value

# ── DRAWING HELPERS ───────────────────────────────────────────────────────────


def draw_crosshair(frame, cx, cy, color, size=18, thickness=2):
    cv2.line(frame, (cx - size, cy), (cx + size, cy), color, thickness)
    cv2.line(frame, (cx, cy - size), (cx, cy + size), color, thickness)
    cv2.circle(frame, (cx, cy), size + 4, color, 1)


def draw_hud(frame, state, x_err, y_err, lost_count, frame_w, frame_h):
    color_map = {
        "IDLE":     (180, 180, 180),
        "LOCKED":   (0, 255, 80),
        "COASTING": (0, 200, 255),
        "LOST":     (0, 60, 255),
    }
    color = color_map.get(state, (255, 255, 255))

    cv2.putText(frame, f"STATE : {state}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    if state in ("LOCKED", "COASTING"):
        cv2.putText(frame, f"x_err : {x_err:+.3f}", (10, 56),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, f"y_err : {y_err:+.3f}", (10, 78),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    if state == "COASTING":
        cv2.putText(frame, f"lost  : {lost_count}/{LOST_FRAME_LIMIT}", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

    cv2.drawMarker(frame, (frame_w // 2, frame_h // 2),
                   (60, 60, 60), cv2.MARKER_CROSS, 12, 1)

    cv2.putText(frame, "L-click: lock | R-click: clear | Q: quit",
                (10, frame_h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 140, 140), 1)

# ── MAIN ──────────────────────────────────────────────────────────────────────


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Check CAMERA_INDEX in config.")
        return

    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Cannot read from camera.")
        return

    frame_h, frame_w = frame.shape[:2]
    half_patch = PATCH_SIZE // 2

    # State
    state = "IDLE"
    tracker = None
    kf = None
    target_cx = 0
    target_cy = 0
    lost_count = 0

    # Smoothed error output (persists across frames for EMA)
    x_err = 0.0
    y_err = 0.0

    click_point = None

    def on_mouse(event, x, y, flags, param):
        nonlocal click_point, state, tracker, kf, lost_count, x_err, y_err

        if event == cv2.EVENT_LBUTTONDOWN:
            click_point = (x, y)

        elif event == cv2.EVENT_RBUTTONDOWN:
            state = "IDLE"
            tracker = None
            kf = None
            lost_count = 0
            x_err = 0.0
            y_err = 0.0
            print("[INFO] Target cleared.")

    cv2.namedWindow("Turret Tracker V1.1")
    cv2.setMouseCallback("Turret Tracker V1.1", on_mouse)

    print("[INFO] System ready. Left-click to lock a target.")
    print(f"[INFO] EMA_ALPHA={EMA_ALPHA}  DEADZONE={DEADZONE}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── Handle new click ──────────────────────────────────────────────────
        if click_point is not None:
            cx, cy = click_point
            click_point = None

            x1 = max(0, cx - half_patch)
            y1 = max(0, cy - half_patch)
            x2 = min(frame_w, cx + half_patch)
            y2 = min(frame_h, cy + half_patch)
            w = x2 - x1
            h = y2 - y1

            if w > 10 and h > 10:
                tracker = cv2.TrackerCSRT_create()
                tracker.init(frame, (x1, y1, w, h))

                kf = create_kalman()
                init_state = np.array([[cx], [cy], [0], [0]], dtype=np.float32)
                kf.statePre = init_state.copy()
                kf.statePost = init_state.copy()
                kf.errorCovPre = np.eye(4, dtype=np.float32)
                kf.errorCovPost = np.eye(4, dtype=np.float32)

                target_cx = cx
                target_cy = cy
                lost_count = 0
                state = "LOCKED"

                # Seed EMA at current position so it doesn't sweep from 0
                x_err = (cx - frame_w / 2) / (frame_w / 2)
                y_err = (cy - frame_h / 2) / (frame_h / 2)

                print(f"[INFO] Locked onto ({cx}, {cy})")

        # ── Tracking ──────────────────────────────────────────────────────────
        if state in ("LOCKED", "COASTING") and tracker is not None:
            success, bbox = tracker.update(frame)

            if success:
                bx, by, bw, bh = [int(v) for v in bbox]
                cx = bx + bw // 2
                cy = by + bh // 2
                target_cx, target_cy = kalman_update(kf, cx, cy)
                lost_count = 0
                state = "LOCKED"

            else:
                lost_count += 1
                target_cx, target_cy = kalman_predict_only(kf)

                if lost_count >= LOST_FRAME_LIMIT:
                    state = "LOST"
                    tracker = None
                    kf = None
                    lost_count = 0
                    x_err = 0.0
                    y_err = 0.0
                    print("[INFO] Target lost.")
                else:
                    state = "COASTING"

        # ── Error computation: Kalman -> EMA -> Deadzone ───────────────────────
        if state in ("LOCKED", "COASTING"):
            # Raw normalized error from Kalman output
            raw_x = (target_cx - frame_w / 2) / (frame_w / 2)
            raw_y = (target_cy - frame_h / 2) / (frame_h / 2)

            # EMA smoothing (low-pass)
            x_err = ema(x_err, raw_x, EMA_ALPHA)
            y_err = ema(y_err, raw_y, EMA_ALPHA)

            # Deadzone (kills micro-vibration on still target)
            x_out = apply_deadzone(x_err, DEADZONE)
            y_out = apply_deadzone(y_err, DEADZONE)

            print(f"\r[TARGET] x={x_out:+.3f}  y={y_out:+.3f}  "
                  f"pos=({target_cx},{target_cy})   ", end="", flush=True)

        # ── Draw ──────────────────────────────────────────────────────────────
        display = frame.copy()

        if state == "LOCKED":
            draw_crosshair(display, target_cx, target_cy, (0, 255, 80))
        elif state == "COASTING":
            draw_crosshair(display, target_cx, target_cy, (0, 200, 255))

        draw_hud(display, state, x_err, y_err, lost_count, frame_w, frame_h)

        cv2.imshow("Turret Tracker V1.1", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Exited cleanly.")


if __name__ == "__main__":
    main()
