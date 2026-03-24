import time
import yaml
import cv2

from utils.visualizer import Visualizer
from hardware.camera import Camera
from vision.detector import Detector
from vision.tracker import Tracker
from vision.vision_node import VisionNode

from control.pid import PID
from control.controller import Controller

from comm.comm_node import CommNode

from utils.time_utils import DeltaTimer


def load_config(path="config/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()

    # --- Camera ---
    cam_cfg = config["camera"]
    camera = Camera(
        index=cam_cfg["index"],
        width=cam_cfg["width"],
        height=cam_cfg["height"]
    )
    cv2.waitKey(1)
    # --- Vision ---
    detector = Detector(
        model_path=config["yolo"]["model"],
        conf_threshold=config["yolo"]["conf_threshold"]
    )

    tracker = Tracker()
    vision = VisionNode(detector, tracker)

    # --- Control ---
    pid_pan = PID(**config["pid"]["pan"])
    pid_tilt = PID(**config["pid"]["tilt"])
    controller = Controller(pid_pan, pid_tilt)

    # --- Communication ---
    comm = CommNode(config)

    # --- Visualization ---
    visualizer = Visualizer()

    # --- Timing ---
    timer = DeltaTimer()

    print("System started... Press ESC to exit.")

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            dt = timer.dt()


            # --- Vision ---
           # --- KEEP UI ALIVE FIRST ---
            cv2.imshow("UGV Turret System", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

            # --- Vision ---
            target, detection = vision.process(frame.copy())

            command = None

            # --- Control ---
            if target is not None:
                command = controller.update(target, dt)
                comm.send_command(command)

            # --- Draw AFTER processing ---
            frame = visualizer.draw(frame, detection, target, command)

            # --- Yield to OS ---
            time.sleep(0.001)

            # --- Exit condition ---
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                break

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()