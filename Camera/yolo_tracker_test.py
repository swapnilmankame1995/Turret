import cv2
import time
from ultralytics import YOLO

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
model = YOLO("yolov8n.pt")

tracker = None
tracking = False

frame_count = 0
detect_every = 5

prev_time = time.time()

target_x = None
target_y = None

current_detections = []
latest_frame = None

# --- tracking stability ---
lost_counter = 0
max_lost = 10  # tolerance for lost frames


# --- Mouse callback ---
def mouse_callback(event, x, y, flags, param):
    global tracking, tracker, target_x, target_y, lost_counter

    # --- SELECT TARGET ---
    if event == cv2.EVENT_LBUTTONDOWN:
        patch_size = 80  # bigger patch = more stable

        x1 = max(0, x - patch_size // 2)
        y1 = max(0, y - patch_size // 2)

        w = patch_size
        h = patch_size

        try:
            tracker = cv2.legacy.TrackerKCF_create()
        except:
            tracker = cv2.TrackerKCF_create()

        tracker.init(latest_frame, (x1, y1, w, h))
        tracking = True
        lost_counter = 0

        print("Tracking point selected")

    # --- DESELECT TARGET ---
    elif event == cv2.EVENT_RBUTTONDOWN:
        tracking = False
        tracker = None
        target_x = None
        target_y = None
        print("Tracking stopped")


cv2.namedWindow("Targeting System")
cv2.setMouseCallback("Targeting System", mouse_callback)


while True:
    ret, frame = cap.read()
    if not ret:
        break

    latest_frame = frame.copy()
    frame_count += 1

    # --- YOLO (AWARENESS ONLY) ---
    if frame_count % detect_every == 0:
        results = model.predict(
            frame,
            device="cuda",
            imgsz=416,
            conf=0.6,
            verbose=False
        )

        current_detections = []

        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                continue

            for b in r.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0])
                current_detections.append((x1, y1, x2, y2))

    # --- DRAW YOLO BOXES ---
    for (x1, y1, x2, y2) in current_detections:
        cv2.rectangle(frame, (x1, y1), (x2, y2),
                      (255, 0, 0), 1)

    # --- TRACKING ---
    if tracking and tracker is not None:
        success, box = tracker.update(frame)

        if success:
            x, y, w, h = map(int, box)

            # --- sanity checks ---
            if w < 5 or h < 5:
                lost_counter += 1
            elif x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
                lost_counter += 1
            else:
                lost_counter = 0  # reset if good

                cv2.rectangle(frame, (x, y), (x + w, y + h),
                              (0, 255, 0), 2)

                cx = x + w / 2
                cy = y + h / 2

                h_frame, w_frame, _ = frame.shape
                target_x = (cx - w_frame / 2) / (w_frame / 2)
                target_y = (cy - h_frame / 2) / (h_frame / 2)

                cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)

        else:
            lost_counter += 1

        # --- STOP ONLY AFTER MULTIPLE FAILURES ---
        if lost_counter > max_lost:
            tracking = False
            tracker = None
            target_x = None
            target_y = None
            print("Tracking lost")

    # --- FPS ---
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    cv2.putText(frame, f"FPS: {int(fps)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2)

    # --- DISPLAY TARGET ---
    if target_x is not None:
        text = f"X: {target_x:.2f} Y: {target_y:.2f}"
        cv2.putText(frame, text,
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2)

    cv2.imshow("Targeting System", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
