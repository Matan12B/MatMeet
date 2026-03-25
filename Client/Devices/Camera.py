import cv2
import threading
import numpy as np


class CameraControl:
    """
    Threaded camera capture class.
    Continuously captures frames from the webcam, encodes them as JPEG bytes.
    """

    def __init__(self, width=320, height=240, jpeg_quality=60):
        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality

        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.last_frame = None
        self.running = False
        self.lock = threading.Lock()
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]

    def start(self):
        """Start the camera capture thread."""
        if not self.running:
            self.running = True
            threading.Thread(target=self._capture_loop, daemon=True).start()
            print("Camera started.")

    def stop(self):
        """Stop the camera capture."""
        if self.running:
            self.running = False
            self.cam.release()
            print("Camera stopped.")

    def _capture_loop(self):
        """Continuously capture frames, resize, encode to JPEG, and store bytes ready to send."""
        while self.running:
            ret, frame = self.cam.read()
            if not ret:
                continue

            try:
                # Resize to desired size (478x359)
                frame_resized = cv2.resize(frame, (self.width, self.height))

                # Encode as JPEG directly
                success, encoded_frame = cv2.imencode('.jpg', frame_resized, self.encode_param)
                if not success:
                    continue

                # Convert to bytes and store
                frame_bytes = encoded_frame.tobytes()
                with self.lock:
                    self.last_frame = frame_bytes

            except Exception as e:
                print(f"Camera capture error: {e}")

    def get_frame(self):
        """Return the latest JPEG-encoded frame bytes."""
        with self.lock:
            return self.last_frame


# Test the camera class
if __name__ == "__main__":
    cam = CameraControl(width=320, height=240)
    cam.start()

    try:
        while True:
            frame_bytes = cam.get_frame()
            if frame_bytes is not None:
                # Decode JPEG bytes for display
                frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()