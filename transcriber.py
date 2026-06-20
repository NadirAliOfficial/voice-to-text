from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size="small", language=None):
        print(f"Loading Whisper {model_size} model...")
        self.model    = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = language
        print("Model ready.")

    def transcribe(self, audio_array):
        segments, info = self.model.transcribe(
            audio_array,
            language=self.language,

            # speed: greedy decoding — no beam search overhead
            beam_size=1,
            temperature=0,

            # quality
            condition_on_previous_text=False,
            no_speech_threshold=0.5,
            compression_ratio_threshold=2.4,

            # skip silence
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 250},

            initial_prompt="Transcribe spoken words exactly as heard.",
        )
        text = " ".join(s.text for s in segments).strip()
        return text, info.language
