import cv2


class Visualizer:
    def __init__(self):
        pass

    def draw(self, frame, detection=None, target=None, command=None):
        h, w, _ = frame.shape

        # --- Draw center crosshair ---
        cx = w // 2
        cy = h // 2
        cv2.drawMarker(frame, (cx, cy), (255, 255, 255), markerType=cv2.MARKER_CROSS, thickness=2)

        # --- Draw detection box (YOLO) ---
        if detection is not None:
            cv2.rectangle(
                frame,
                (detection.x1, detection.y1),
                (detection.x2, detection.y2),
                (0, 255, 0),
                2
            )

        # --- Draw target point ---
        if target is not None:
            tx = int((target.x * w / 2) + w / 2)
            ty = int((target.y * h / 2) + h / 2)

            cv2.circle(frame, (tx, ty), 6, (0, 0, 255), -1)

        # --- Draw command text ---
        if command is not None:
            text = f"PAN: {command.pan:.2f} | TILT: {command.tilt:.2f}"
            cv2.putText(frame, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        return frame