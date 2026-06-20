"""
CLI version — no menu bar, no hotkey.
Press Enter to start recording, Enter again to stop and transcribe.
Output is printed and copied to clipboard.

Usage:
    python cli.py
    python cli.py --model medium
    python cli.py --lang en
"""

import argparse
import pyperclip
from recorder import AudioRecorder
from transcriber import Transcriber


def run(model_size="small", language=None):
    recorder     = AudioRecorder()
    transcriber  = Transcriber(model_size, language)

    print("\nVoice Typer CLI")
    print("Press ENTER to start recording, ENTER again to stop.\n")

    while True:
        try:
            input("[ Press ENTER to record ]")
            recorder.start()
            print("  🔴 Recording... (press ENTER to stop)")
            input()
            audio = recorder.stop()

            if audio is None:
                print("  Too short, try again.\n")
                continue

            print("  ⏳ Transcribing...")
            text, lang = transcriber.transcribe(audio)

            if text:
                print(f"\n  [{lang.upper()}] {text}\n")
                pyperclip.copy(text)
                print("  Copied to clipboard.\n")
            else:
                print("  No speech detected.\n")

        except KeyboardInterrupt:
            print("\nBye.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--lang",  default=None)
    args = parser.parse_args()
    run(args.model, args.lang)
