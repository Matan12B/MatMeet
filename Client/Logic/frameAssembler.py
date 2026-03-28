
import math
import struct
import time
import cv2
import numpy as np
FRAME_PARTS = 4

# frame_id      -> 4 bytes unsigned int
# timestamp     -> 8 bytes double
# total_parts   -> 1 byte
# part_index    -> 1 byte
# payload_size  -> 2 bytes unsigned short
HEADER_FORMAT = "!IdBBH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def split_frame_to_4_packets(frame_id, timestamp, frame_bytes):
    """
    Split encoded frame bytes into 4 UDP packets.

    :param frame_id:
    :param timestamp:
    :param frame_bytes:
    :return:
    """
    packets = []
    chunk_size = math.ceil(len(frame_bytes) / FRAME_PARTS)

    for part_index in range(FRAME_PARTS):
        start = part_index * chunk_size
        end = start + chunk_size
        chunk = frame_bytes[start:end]

        header = struct.pack(
            HEADER_FORMAT,
            frame_id,
            timestamp,
            FRAME_PARTS,
            part_index,
            len(chunk)
        )

        packets.append(header + chunk)

    return packets





class FrameReassembler:
    def __init__(self):
        self.frame_store = {}
        self.FRAME_PARTS = 4
        self.HEADER_FORMAT = "!IdBBH"
        self.HEADER_SIZE = struct.calcsize(self.HEADER_FORMAT)

    def handle_packet(self, packet):
        """
        Return:
        (frame, timestamp) or (None, None)
        """
        if len(packet) < self.HEADER_SIZE:
            return None, None

        try:
            header = packet[:self.HEADER_SIZE]
            payload = packet[self.HEADER_SIZE:]

            frame_id, timestamp, total_parts, part_index, payload_size = struct.unpack(
                self.HEADER_FORMAT,
                header
            )

            if total_parts != self.FRAME_PARTS:
                return None, None

            if payload_size != len(payload):
                return None, None

            if frame_id not in self.frame_store:
                self.frame_store[frame_id] = {
                    "timestamp": timestamp,
                    "total_parts": total_parts,
                    "parts": {},
                    "last_update": time.time()
                }

            self.frame_store[frame_id]["parts"][part_index] = payload
            self.frame_store[frame_id]["last_update"] = time.time()

            if len(self.frame_store[frame_id]["parts"]) == total_parts:
                return self.rebuild_frame(frame_id)

        except Exception as e:
            print("handle_packet error:", e)

        return None, None

    def rebuild_frame(self, frame_id):
        if frame_id not in self.frame_store:
            return None, None

        try:
            frame_data = self.frame_store[frame_id]
            parts = frame_data["parts"]
            timestamp = frame_data["timestamp"]

            full_bytes = b""
            for i in range(self.FRAME_PARTS):
                if i not in parts:
                    return None, None
                full_bytes += parts[i]

            np_arr = np.frombuffer(full_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            del self.frame_store[frame_id]

            return frame, timestamp

        except Exception as e:
            print("rebuild_frame error:", e)
            if frame_id in self.frame_store:
                del self.frame_store[frame_id]
            return None, None

    def cleanup_old_frames(self, max_age=2.0):
        now = time.time()
        old_ids = []

        for frame_id, data in self.frame_store.items():
            if now - data["last_update"] > max_age:
                old_ids.append(frame_id)

        for frame_id in old_ids:
            del self.frame_store[frame_id]