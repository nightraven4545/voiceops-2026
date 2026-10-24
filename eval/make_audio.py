"""Make voice test input with Gnani TTS: practice questions as single files, practice
conversations as sub-folders (one file per turn), plus a silent clip.

  python eval/make_audio.py --out test_audio --questions PQ0003 PQ0048 --conversations PC002
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rules import DATASET  # noqa: E402
from src.voice import speak  # noqa: E402


def rows(name):
    with open(DATASET / "practice" / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("test_audio"))
    ap.add_argument("--questions", nargs="*", default=[])
    ap.add_argument("--conversations", nargs="*", default=[])
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for q in rows("questions.csv"):
        if q["id"] in args.questions:
            speak(q["question"], q["language"], args.out / f"{q['id']}.wav")
            print("wrote", q["id"], q["question"])
    for t in rows("conversations.csv"):
        if t["conversation_id"] in args.conversations:
            folder = args.out / t["conversation_id"]
            folder.mkdir(exist_ok=True)
            speak(t["customer_message"], t["language"], folder / f"turn{t['turn']}.wav")
            print("wrote", t["conversation_id"], t["turn"], t["customer_message"])
    sf.write(args.out / "silence.wav", np.zeros(16000, dtype="int16"), 16000)
