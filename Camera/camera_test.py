import cv2
import time

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # --- FPS calculation ---
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    # --- Get frame center ---
    h, w, _ = frame.shape
    cx = w // 2
    cy = h // 2

    # --- Draw crosshair ---
    cv2.drawMarker(frame, (cx, cy), (0, 255, 0),
                   markerType=cv2.MARKER_CROSS,
                   thickness=2)

    # --- Draw FPS ---
    cv2.putText(frame, f"FPS: {int(fps)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2)

    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
