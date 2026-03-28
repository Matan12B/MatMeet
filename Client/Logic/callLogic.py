import threading
import time
import cv2
import queue
import numpy as np

from Client.Devices.Camera import CameraControl
from Client.Devices.Microphone import Microphone
from Client.Devices.AudioOutputDevice import AudioOutput
from Client.GUI.VideoDisplay import VideoDisplay
from Client.Comms.videoComm import VideoComm
from Client.Comms.audioComm import AudioClient
from Client.Protocol import clientProtocol
from Common.Cipher import AESCipher
from Client.Comms.ClientComm import ClientComm


class CallLogic:
    def __init__(self, port, meeting_key, comm, host_ip):
        self.open_clients = {}   # ip -> port
        self.msgs_from_host = queue.Queue()
        self.display = VideoDisplay()
        self.comm_with_server = comm
        self.AES = AESCipher(meeting_key)

        self.comm_with_host = ClientComm(host_ip, port, self.msgs_from_host, self.AES)
        self.video_comm = VideoComm(self.AES, self.open_clients)
        self.audio_comm = AudioClient(host_ip, self.AES)

        # host is always connected
        self.open_clients[host_ip] = port
        self.host_ip = host_ip

        # left as requested
        self.ip = "10.0.0.13"

        # GUI queues
        self.UI_queue = queue.Queue()
        self.remote_video_queue = queue.Queue()

        # latest frames by client
        self.latest_remote_frames = {}

        # restored commands table
        self.commands = {
            "ha": self.handle_audio,
            "hv": self.handle_video_msg,   # legacy/support path
            "hj": self.handle_join,
            "hd": self.handle_disconnect,
            "gmst": self.get_meeting_start_time
        }

        self.camera = CameraControl(jpeg_quality=5)
        self.mic = Microphone(50)
        self.AudioOutput = AudioOutput()
        self.encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 5]

        self.sync_buffer = {}

        self.meeting_start_time = None
        self.running = True
        self.send_queue = queue.Queue(maxsize=1)
        self.audio_play_queue = queue.Queue()

    def start(self):
        print("Starting guest call...")

        self.camera.start()
        self.mic.start()
        self.mic.unmute()

        self.send_queue = queue.Queue(maxsize=1)

        threading.Thread(target=self.handle_msgs_from_host, daemon=True).start()
        threading.Thread(target=self.receive_video_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()
        threading.Thread(target=self.audio_send_loop, daemon=True).start()
        threading.Thread(target=self.receive_audio_loop, daemon=True).start()
        threading.Thread(target=self.audio_play_loop, daemon=True).start()

        try:
            while self.running:
                frame = self.camera.get_frame()

                if frame is None:
                    time.sleep(0.005)
                    continue

                frame = frame.copy()

                while self.UI_queue.qsize() >= 1:
                    try:
                        self.UI_queue.get_nowait()
                    except queue.Empty:
                        break

                self.UI_queue.put(frame)

                if self.meeting_start_time is not None:
                    timestamp = time.time() - self.meeting_start_time

                    if self.send_queue.full():
                        try:
                            self.send_queue.get_nowait()
                        except queue.Empty:
                            pass

                    try:
                        self.send_queue.put_nowait((frame, timestamp))
                    except queue.Full:
                        pass

                time.sleep(0.01)

        except Exception as e:
            print("guest start loop error:", e)
        finally:
            self.cleanup()

    def send_loop(self):
        while self.running:
            try:
                frame, timestamp = self.send_queue.get(timeout=1)

                ok, encoded = cv2.imencode(".jpg", frame, self.encode_params)
                if not ok:
                    continue

                frame_bytes = encoded.tobytes()
                frame_data = clientProtocol.build_video_msg(timestamp, frame_bytes)
                self.video_comm.send_frame(frame_data)

            except queue.Empty:
                continue
            except Exception as e:
                print("send_loop error:", e)
                time.sleep(0.02)

    def audio_send_loop(self):
        while self.running:
            try:
                if not self.mic.running or self.meeting_start_time is None:
                    time.sleep(0.01)
                    continue

                audio_chunk = self.mic.record()
                if not audio_chunk:
                    continue

                timestamp = time.time() - self.meeting_start_time
                msg = clientProtocol.build_audio_msg(timestamp, audio_chunk, self.ip)
                self.audio_comm.send_audio(msg)

            except Exception as e:
                print("audio_send_loop error:", e)
                time.sleep(0.02)

    def receive_video_loop(self):
        """
        Receive remote video and push it directly to GUI queue.
        """
        while self.running:
            try:
                while not self.video_comm.frameQ.empty():
                    try:
                        video_data, timestamp, addr = self.video_comm.frameQ.get_nowait()
                    except queue.Empty:
                        break

                    client_ip = addr[0]

                    if client_ip not in self.open_clients:
                        self.open_clients[client_ip] = self.open_clients.get(self.host_ip, 0)

                    frame = None
                    try:
                        if isinstance(video_data, np.ndarray):
                            frame = video_data
                        elif isinstance(video_data, (bytes, bytearray)):
                            frame = cv2.imdecode(
                                np.frombuffer(video_data, np.uint8),
                                cv2.IMREAD_COLOR
                            )
                    except Exception as e:
                        print("decode error:", e)
                        frame = None

                    if frame is None:
                        continue

                    self.latest_remote_frames[client_ip] = frame

                    try:
                        if client_ip not in self.sync_buffer:
                            self.sync_buffer[client_ip] = {}

                        self.sync_buffer[client_ip][float(timestamp)] = {
                            "video": frame,
                            "audio": None
                        }
                        self._prune_old_frames(client_ip, keep=20)
                    except Exception:
                        pass

                    while self.remote_video_queue.qsize() >= 5:
                        try:
                            self.remote_video_queue.get_nowait()
                        except queue.Empty:
                            break

                    self.remote_video_queue.put((client_ip, frame))

                time.sleep(0.005)

            except Exception as e:
                print("receive_video_loop error:", e)
                time.sleep(0.05)

    def receive_audio_loop(self):
        """
        Receive remote audio and queue it for playback immediately.
        """
        while self.running:
            try:
                while not self.audio_comm.audio_queue.empty():
                    try:
                        audio_bytes, timestamp, sender_ip = self.audio_comm.audio_queue.get_nowait()
                    except queue.Empty:
                        break

                    client_ip = sender_ip

                    if client_ip not in self.open_clients:
                        self.open_clients[client_ip] = self.open_clients.get(self.host_ip, 0)

                    try:
                        if client_ip not in self.sync_buffer:
                            self.sync_buffer[client_ip] = {}

                        self.sync_buffer[client_ip][float(timestamp)] = {
                            "video": None,
                            "audio": audio_bytes
                        }
                        self._prune_old_frames(client_ip, keep=20)
                    except Exception:
                        pass

                    while self.audio_play_queue.qsize() >= 10:
                        try:
                            self.audio_play_queue.get_nowait()
                        except queue.Empty:
                            break

                    self.audio_play_queue.put(audio_bytes)

                time.sleep(0.005)

            except Exception as e:
                print("receive_audio_loop error:", e)
                time.sleep(0.05)

    def audio_play_loop(self):
        """
        Play audio in a separate thread.
        """
        while self.running:
            try:
                audio = self.audio_play_queue.get(timeout=1)
                if audio is not None:
                    self.AudioOutput.play_bytes(audio)
            except queue.Empty:
                continue
            except Exception as e:
                print("audio_play_loop error:", e)
                time.sleep(0.05)

    def _prune_old_frames(self, client_ip, keep=20):
        if client_ip not in self.sync_buffer:
            return

        timestamps = self.sync_buffer[client_ip]
        if len(timestamps) <= keep:
            return

        latest = sorted(timestamps.keys(), reverse=True)[:keep]
        latest = set(latest)

        for ts in list(timestamps.keys()):
            if ts not in latest:
                del timestamps[ts]

    def handle_msgs_from_client_logic(self, opcode, data):
        try:
            if opcode in self.commands:
                self.commands[opcode](data)
        except Exception as e:
            print(f"Error handling message: {e}")

    def handle_msgs_from_host(self):
        while self.running:
            try:
                msg = self.msgs_from_host.get(timeout=1)
            except queue.Empty:
                continue
            except Exception as e:
                print("host queue error:", e)
                time.sleep(0.05)
                continue

            print(f"Received message from host: {msg}")

            try:
                opcode, data = clientProtocol.unpack(msg)
            except Exception as e:
                print("unpack error:", e)
                continue

            if opcode in self.commands:
                try:
                    self.commands[opcode](data)
                except Exception as e:
                    print(f"Error in command {opcode}: {e}")

    def get_meeting_start_time(self, data):
        try:
            if isinstance(data, list):
                self.meeting_start_time = float(data[0])
            else:
                self.meeting_start_time = float(data)

            print("meeting start time:", self.meeting_start_time)
        except Exception as e:
            print("meeting start time parse error:", e)

    def handle_video_msg(self, data):
        """
        Legacy support in case video ever comes through self.commands.
        Expected data like [client_ip, username, timestamp, frame]
        """
        try:
            client_ip = data[0]
            username = data[1]
            timestamp = data[2]
            frame = data[3]
        except Exception as e:
            print("video msg parse error:", e)
            return

        self.handle_video(client_ip, username, timestamp, frame)

    def handle_video(self, client_ip, username, timestamp, frame):
        self.latest_remote_frames[client_ip] = frame

        while self.remote_video_queue.qsize() >= 5:
            try:
                self.remote_video_queue.get_nowait()
            except queue.Empty:
                break

        self.remote_video_queue.put((client_ip, frame))

    def handle_audio(self, data):
        try:
            client_ip = data[0]
            username = data[1]
            timestamp = data[2]
            audio = data[3]
        except Exception as e:
            print("audio msg parse error:", e)
            return

        while self.audio_play_queue.qsize() >= 10:
            try:
                self.audio_play_queue.get_nowait()
            except queue.Empty:
                break

        self.audio_play_queue.put(audio)

    def handle_join(self, data):
        try:
            ip = data[0]
            port = int(data[1])
        except Exception as e:
            print("join parse error:", e)
            return

        print(f"{ip} joined the call")
        self.open_clients[ip] = port

    def handle_disconnect(self, data):
        try:
            ip = data[0]
            username = data[1] if len(data) > 1 else ip
        except Exception as e:
            print("disconnect parse error:", e)
            return

        print(f"{username} left the call")

        if ip in self.open_clients:
            del self.open_clients[ip]

        if ip in self.sync_buffer:
            del self.sync_buffer[ip]

        if ip in self.latest_remote_frames:
            del self.latest_remote_frames[ip]

        try:
            self.video_comm.remove_user(ip, 0)
        except Exception:
            pass

    def leave_call(self):
        self.cleanup()

    def cleanup(self):
        if not self.running:
            return

        print("Closing guest call...")
        self.running = False

        try:
            if hasattr(self, "camera"):
                self.camera.stop()
        except Exception as e:
            print("camera stop error:", e)

        try:
            if hasattr(self, "mic"):
                self.mic.stop()
        except Exception as e:
            print("mic stop error:", e)

        try:
            if hasattr(self, "AudioOutput"):
                self.AudioOutput.stop()
        except Exception as e:
            print("audio output stop error:", e)

        try:
            if hasattr(self, "video_comm"):
                self.video_comm.close()
        except Exception as e:
            print("video close error:", e)

        try:
            if hasattr(self, "audio_comm") and hasattr(self.audio_comm, "close_client"):
                self.audio_comm.close_client()
        except Exception as e:
            print("audio close error:", e)

        try:
            if hasattr(self, "comm_with_host") and hasattr(self.comm_with_host, "close_client"):
                self.comm_with_host.close_client()
        except Exception as e:
            print("host comm close error:", e)

        time.sleep(0.1)