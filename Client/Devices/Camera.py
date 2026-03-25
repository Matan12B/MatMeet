import cv2
import pickle
import threading


class CameraControl:
    def __init__(self, width=320, height=240):
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.last_frame = None
        self.running = False
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        self.lock = threading.Lock()

    def start(self):
        """

        :return:
        """
        if not self.running:
            self.running = True
            threading.Thread(target=self._capture, daemon=True).start()
            print("Camera started.")

    def stop(self):
        """

        :return:
        """
        if self.running:
            self.running = False
            self.cam.release()
            print("Camera stopped.")

    def _capture(self):
        """

        :return:
        """
        while self.running:
            ret, frame = self.cam.read()
            if not ret:
                continue
            result, encoded_frame = cv2.imencode('.jpg', frame, self.encode_param)
            if not result:
                continue
            data = pickle.dumps(encoded_frame)
            with self.lock:
                self.last_frame = data

    def get_frame(self):
        with self.lock:
            return self.last_frame

def main():
    cam = CameraControl()
    cam.start()

if __name__ == "__main__":
    main()