"""
UGV Turret Targeting System — V2.1 (PID Simulation Mode)
==========================================================
Bug fixes from V2:
  - Crosshair now visually responds to PID output (simulation mode)
  - Key bindings changed to avoid OpenCV conflicts on Windows

How simulation mode works:
  The tracker gives the TRUE target position (green crosshair).
  The PID crosshair (orange) starts at frame center — where the turret points.
  Each frame the PID drives the orange crosshair TOWARD the green target.
  This simulates what a real motor would do — you can see overshoot, oscillation,
  sluggishness — all before touching any hardware.

  When motors are connected:
    - Remove sim_x / sim_y update logic
    - Send pan_cmd / tilt_cmd straight to serial/ROS2
    - The camera feedback loop does the rest naturally

Tuning hotkeys (click OpenCV window first):
  U / J   — Kp  up / down  (+/- 0.05)
  I / K   — Ki  up / down  (+/- 0.005)
  O / L   — Kd  up / down  (+/- 0.01)
  Q       — quit

Controls:
  Left-click   : lock target
  Right-click  : deselect
"""

import cv2
import numpy as np
import time
from pid_controller import TurretPID

# ── CONFIG ────────────────────────────────────────────────────────────────────

CAMERA_INDEX = 0
PATCH_SIZE = 80
LOST_FRAME_LIMIT = 15

EMA_ALPHA = 0.12
DEADZONE = 0.01

KP_INIT = 0.6
KI_INIT = 0.01
KD_INIT = 0.08

# Simulation: pixels the turret moves per unit of PID output per frame
# Raise if sim crosshair moves too slowly, lower if too fast
SIM_SPEED = 8.0

# ── KALMAN ────────────────────────────────────────────────────────────────────


def create_kalman():
    kf = cv2.KalmanFilter(4, 2)
    kf.measurementMatrix = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
    kf.transitionMatrix = np.array(
        [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01
    kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 4.0
    kf.errorCovPost = np.eye(4, dtype=np.float32)
    return kf


def kalman_update(kf, cx, cy):
    kf.correct(np.array([[np.float32(cx)], [np.float32(cy)]]))
    p = kf.predict()
    return int(p[0].item()), int(p[1].item())


def kalman_predict_only(kf):
    p = kf.predict()
    return int(p[0].item()), int(p[1].item())

# ── SMOOTHING ─────────────────────────────────────────────────────────────────


def ema(prev, new, alpha):
    return alpha * new + (1.0 - alpha) * prev


def deadzone(v, thresh):
    return 0.0 if abs(v) < thresh else v

# ── DRAWING ───────────────────────────────────────────────────────────────────


def draw_crosshair(frame, cx, cy, color, size=18, thickness=2):
    cv2.line(frame, (cx-size, cy), (cx+size, cy), color, thickness)
    cv2.line(frame, (cx, cy-size), (cx, cy+size), color, thickness)
    cv2.circle(frame, (cx, cy), size+4, color, 1)


def draw_sim_crosshair(frame, cx, cy):
    size = 14
    cv2.line(frame, (cx-size, cy), (cx+size, cy), (0, 140, 255), 2)
    cv2.line(frame, (cx, cy-size), (cx, cy+size), (0, 140, 255), 2)
    cv2.circle(frame, (cx, cy), size+4, (0, 140, 255), 1)
    cv2.putText(frame, "TURRET", (cx+size+4, cy-4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 140, 255), 1)


def bar(frame, x, y, value, label, color):
    w = 80
    cv2.rectangle(frame, (x, y), (x+w, y+10), (60, 60, 60), -1)
    filled = int(abs(value) * w)
    bx = x if value >= 0 else x + w - filled
    if filled > 0:
        cv2.rectangle(frame, (bx, y), (bx+filled, y+10), color, -1)
    cv2.putText(frame, f"{label}{value:+.2f}", (x+w+4, y+9),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)


def translucent_rect(frame, x1, y1, x2, y2, color=(30, 30, 30), alpha=0.55):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)


def draw_hud(frame, state, x_err, y_err, pan_cmd, tilt_cmd,
             debug, kp, ki, kd, lost_count, sim_err_x, sim_err_y, fw, fh):

    color_map = {
        "IDLE":     (180, 180, 180),
        "LOCKED":   (0, 255, 80),
        "COASTING": (0, 200, 255),
        "LOST":     (0, 60, 255),
    }
    sc = color_map.get(state, (255, 255, 255))

    left_h = 185 if state in ("LOCKED", "COASTING") else 38
    translucent_rect(frame, 4, 6, 265, left_h)
    translucent_rect(frame, fw-192, 6, fw-4, 72)
    translucent_rect(frame, 4, fh-24, fw-4, fh-2)

    cv2.putText(frame, f"STATE : {state}", (10, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, sc, 2)

    if state in ("LOCKED", "COASTING"):
        cv2.putText(frame, f"target  x={x_err:+.3f}  y={y_err:+.3f}", (10, 46),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 80), 1)
        cv2.putText(frame, f"turret  x={sim_err_x:+.3f}  y={sim_err_y:+.3f}", (10, 62),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 140, 255), 1)

        bar(frame, 10, 74,  pan_cmd,  "pan  ", (0, 200, 255))
        bar(frame, 10, 88,  tilt_cmd, "tilt ", (0, 255, 150))

        p_val = debug["pan"]["p"]
        i_val = debug["pan"]["i"]
        d_val = debug["pan"]["d"]
        cv2.putText(frame, "PID breakdown (pan axis):", (10, 114),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1)
        cv2.putText(frame, f"P={p_val:+.3f}  I={i_val:+.3f}  D={d_val:+.3f}",
                    (10, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1)

        bar(frame, 10, 138, min(max(p_val, -1), 1), "P ", (100, 200, 100))
        bar(frame, 10, 151, min(max(i_val, -1), 1), "I ", (200, 200, 100))
        bar(frame, 10, 164, min(max(d_val, -1), 1), "D ", (200, 100, 100))

    if state == "COASTING":
        cv2.putText(frame, f"coast: {lost_count}/{LOST_FRAME_LIMIT}", (10, 182),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1)

    gx = fw - 188
    cv2.putText(frame, f"Kp={kp:.3f}  [U/J]", (gx, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 100), 1)
    cv2.putText(frame, f"Ki={ki:.4f} [I/K]", (gx, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 100), 1)
    cv2.putText(frame, f"Kd={kd:.3f}  [O/L]", (gx, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 100), 1)

    cv2.drawMarker(frame, (fw//2, fh//2), (60, 60, 60),
                   cv2.MARKER_CROSS, 12, 1)
    cv2.putText(frame, "GREEN=target  ORANGE=turret(sim)",
                (fw//2 - 120, fh//2 - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (140, 140, 140), 1)

    cv2.putText(frame,
                "L-click:lock  R-click:clear  U/J=Kp  I/K=Ki  O/L=Kd  Q:quit",
                (10, fh-8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)

# ── MAIN ──────────────────────────────────────────────────────────────────────


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Cannot read frame.")
        return

    fh, fw = frame.shape[:2]
    half_patch = PATCH_SIZE // 2

    state = "IDLE"
    tracker = None
    kf = None
    target_cx = fw // 2
    target_cy = fh // 2
    lost_count = 0
    x_err = 0.0
    y_err = 0.0

    # Simulated turret position — starts at frame center
    sim_x = float(fw // 2)
    sim_y = float(fh // 2)
    sim_err_x = 0.0
    sim_err_y = 0.0

    pid = TurretPID(kp=KP_INIT, ki=KI_INIT, kd=KD_INIT)
    kp, ki, kd = KP_INIT, KI_INIT, KD_INIT
    pan_cmd = 0.0
    tilt_cmd = 0.0
    debug = {"pan":  {"p": 0, "i": 0, "d": 0, "out": 0},
             "tilt": {"p": 0, "i": 0, "d": 0, "out": 0}}

    click_point = None

    def on_mouse(event, x, y, flags, param):
        nonlocal click_point, state, tracker, kf, lost_count
        nonlocal x_err, y_err, pan_cmd, tilt_cmd, sim_x, sim_y

        if event == cv2.EVENT_LBUTTONDOWN:
            click_point = (x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            state = "IDLE"
            tracker = None
            kf = None
            lost_count = 0
            x_err = y_err = 0.0
            pan_cmd = tilt_cmd = 0.0
            sim_x = float(fw // 2)
            sim_y = float(fh // 2)
            pid.reset()
            print("[INFO] Target cleared.")

    cv2.namedWindow("Turret V2.1 — PID Sim")
    cv2.setMouseCallback("Turret V2.1 — PID Sim", on_mouse)

    print("[INFO] Ready.")
    print("[INFO] GREEN crosshair = target (tracker)")
    print("[INFO] ORANGE crosshair = simulated turret response (PID)")
    print("[INFO] Gains: U/J=Kp  I/K=Ki  O/L=Kd")
    print(f"[INFO] Starting gains — Kp={kp}  Ki={ki}  Kd={kd}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── New click ─────────────────────────────────────────────────────
        if click_point is not None:
            cx, cy = click_point
            click_point = None
            x1 = max(0, cx-half_patch)
            y1 = max(0, cy-half_patch)
            x2 = min(fw, cx+half_patch)
            y2 = min(fh, cy+half_patch)
            w, h = x2-x1, y2-y1

            if w > 10 and h > 10:
                tracker = cv2.TrackerCSRT_create()
                tracker.init(frame, (x1, y1, w, h))
                kf = create_kalman()
                init = np.array([[cx], [cy], [0], [0]], dtype=np.float32)
                kf.statePre = kf.statePost = init.copy()
                kf.errorCovPre = kf.errorCovPost = np.eye(4, dtype=np.float32)
                target_cx = cx
                target_cy = cy
                lost_count = 0
                state = "LOCKED"
                x_err = (cx - fw/2) / (fw/2)
                y_err = (cy - fh/2) / (fh/2)
                sim_x = float(fw // 2)
                sim_y = float(fh // 2)
                pid.reset()
                print(f"[INFO] Locked ({cx},{cy})")

        # ── Tracking ──────────────────────────────────────────────────────
        if state in ("LOCKED", "COASTING") and tracker is not None:
            success, bbox = tracker.update(frame)
            if success:
                bx, by, bw, bh = [int(v) for v in bbox]
                cx = bx + bw//2
                cy = by + bh//2
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
                    x_err = y_err = 0.0
                    pan_cmd = tilt_cmd = 0.0
                    pid.reset()
                    print("[INFO] Target lost.")
                else:
                    state = "COASTING"

        # ── PID update ────────────────────────────────────────────────────
        if state in ("LOCKED", "COASTING"):
            raw_x = (target_cx - fw/2) / (fw/2)
            raw_y = (target_cy - fh/2) / (fh/2)
            x_err = ema(x_err, raw_x, EMA_ALPHA)
            y_err = ema(y_err, raw_y, EMA_ALPHA)

            # Error is from sim turret position to target — not from frame center
            sim_err_x = (target_cx - sim_x) / (fw/2)
            sim_err_y = (target_cy - sim_y) / (fh/2)

            pan_cmd, tilt_cmd, debug = pid.update(sim_err_x, sim_err_y)

            # Move simulated turret by PID output
            sim_x = max(0.0, min(float(fw), sim_x + pan_cmd * SIM_SPEED))
            sim_y = max(0.0, min(float(fh), sim_y + tilt_cmd * SIM_SPEED))

            print(f"\r[CMD] pan={pan_cmd:+.3f}  tilt={tilt_cmd:+.3f} "
                  f"| sim_err x={sim_err_x:+.3f} y={sim_err_y:+.3f}   ",
                  end="", flush=True)

        # ── Draw ──────────────────────────────────────────────────────────
        display = frame.copy()

        if state in ("LOCKED", "COASTING"):
            # Line from turret to target
            cv2.line(display, (int(sim_x), int(sim_y)),
                     (target_cx, target_cy), (80, 80, 80), 1)
            draw_sim_crosshair(display, int(sim_x), int(sim_y))

        if state == "LOCKED":
            draw_crosshair(display, target_cx, target_cy, (0, 255, 80))
        elif state == "COASTING":
            draw_crosshair(display, target_cx, target_cy, (0, 200, 255))

        draw_hud(display, state, x_err, y_err, pan_cmd, tilt_cmd,
                 debug, kp, ki, kd, lost_count, sim_err_x, sim_err_y, fw, fh)

        cv2.imshow("Turret V2.1 — PID Sim", display)

        # ── Keys ──────────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('u'):
            kp = round(kp + 0.05, 3)
        elif key == ord('j'):
            kp = max(0.0, round(kp - 0.05, 3))
        elif key == ord('i'):
            ki = round(ki + 0.005, 4)
        elif key == ord('k'):
            ki = max(0.0, round(ki - 0.005, 4))
        elif key == ord('o'):
            kd = round(kd + 0.01, 3)
        elif key == ord('l'):
            kd = max(0.0, round(kd - 0.01, 3))

        if key in (ord('u'), ord('j'), ord('i'), ord('k'), ord('o'), ord('l')):
            pid.set_gains(kp, ki, kd)
            print(f"\n[GAINS] Kp={kp:.3f}  Ki={ki:.4f}  Kd={kd:.3f}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Exited.")


if __name__ == "__main__":
    main()
