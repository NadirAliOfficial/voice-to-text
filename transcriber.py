from faster_whisper import WhisperModel

MODELS = ["tiny", "base", "small", "medium", "large-v3"]


class Transcriber:
    def __init__(self, model_size="small", language=None):
        print(f"Loading Whisper {model_size} model...")
        self.model    = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = language  # None = auto-detect
        print("Model ready.")

    def transcribe(self, audio_array):
        segments, info = self.model.transcribe(
            audio_array,
            beam_size=5,
            language=self.language,
            vad_filter=True,           # skip silent parts
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(s.text for s in segments).strip()
        return text, info.language
