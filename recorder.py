import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # Whisper requires 16 kHz


class AudioRecorder:
    def __init__(self):
        self._chunks  = []
        self._lock    = threading.Lock()
        self._stream  = None
        self.recording = False

    def start(self):
        self._chunks  = []
        self.recording = True
        self._stream  = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        if self.recording:
            with self._lock:
                self._chunks.append(indata.copy())

    def stop(self):
        self.recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0).flatten()
        return audio if len(audio) > SAMPLE_RATE * 0.3 else None  # skip <0.3s clips
