import sounddevice as sd
import numpy as np


class AudioOutput:
    def __init__(self, rate=44100, channels=2, device_index=None):
        """
        Initialize output device.
        :param rate: Sample rate (e.g. 44100Hz)
        :param channels: Number of channels (1 = mono, 2 = stereo)
        :param device_index: Output device ID (None = default)
        """
        self.rate = rate
        self.channels = channels
        self.device_index = device_index

        self.stream = sd.OutputStream(
            samplerate=self.rate,
            channels=self.channels,
            dtype='int16',
            device=self.device_index
        )
        self.stream.start()

    def play_bytes(self, audio_bytes):
        """Play raw int16 bytes"""
        if self.stream:
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            # Reshape if stereo
            if self.channels > 1:
                audio_data = audio_data.reshape(-1, self.channels)

            self.stream.write(audio_data)

    def stop(self):
        """Close stream and release resources"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    @staticmethod
    def list_devices():
        """List all available audio devices"""
        print(sd.query_devices())

def main():
    a = AudioOutput()
