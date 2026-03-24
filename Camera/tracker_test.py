import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

tracker = None
tracking = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # --- If tracking, update ---
    if tracking and tracker is not None:
        success, box = tracker.update(frame)

        if success:
            x, y, w, h = map(int, box)
            cv2.rectangle(frame, (x, y), (x + w, y + h),
                          (0, 255, 0), 2)
        else:
            tracking = False

    cv2.imshow("Tracker Test", frame)

    key = cv2.waitKey(1) & 0xFF

    # --- Press 's' to select ROI ---
    if key == ord('s'):
        frozen_frame = frame.copy()

        roi = cv2.selectROI("Tracker Test", frozen_frame, False)

        if roi[2] == 0 or roi[3] == 0:
            print("Invalid ROI")
            continue

        try:
            tracker = cv2.legacy.TrackerKCF_create()
        except:
            tracker = cv2.TrackerKCF_create()

        tracker.init(frozen_frame, roi)
        tracking = True

    # --- ESC to exit ---
    elif key == 27:
        break

cap.release()
cv2.destroyAllWindows()
