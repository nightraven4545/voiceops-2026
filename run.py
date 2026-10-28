"""Batch voice run: every customer audio file -> agent reply as text + speech + the chunks used.

  python run.py --input AUDIO_DIR --output OUT_DIR

Audio files directly in AUDIO_DIR are separate calls. Each sub-folder is one conversation:
its files are played to the same agent in natural order (turn1, turn2, ... turn10).
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from src.agent import Agent
from src.voice import speak, transcribe

AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm", ".opus", ".amr", ".mp4", ".3gp", ".wma"}
NOT_HEARD = {"en": "Sorry, I didn't catch that. Could you please say it again?",
             "hi": "माफ़ कीजिए, मैं सुन नहीं पाई। क्या आप फिर से बोल सकते हैं?",
             "hi-en": "Maaf kijiye, main sun nahi paayi. Kya aap phir se bol sakte hain?"}
TROUBLE = {"en": "Sorry, I'm having trouble right now. Please try again in a moment.",
           "hi": "माफ़ कीजिए, अभी कुछ दिक्कत आ रही है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
           "hi-en": "Maaf kijiye, abhi thodi dikkat aa rahi hai. Kripya thodi der baad phir koshish karein."}


def natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def audio_in(folder):
    return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO), key=natural)


def handle(path, agent, out_dir, conversation):
    t0, rec, lang = time.time(), {"file": str(path), "conversation": conversation}, agent.state.lang or "en"
    timings = rec["timings"] = {}
    try:
        heard, heard_hi = transcribe(path)
        timings["stt"] = round(time.time() - t0, 2)
        rec.update(transcript=heard, transcript_hi=heard_hi)
        if not heard.strip() and not (heard_hi or "").strip():
            rec.update(reply=NOT_HEARD[lang], decision="clarify", lang=lang, sources=[], retrieved=[], tool_calls=[])
        else:
            rec.update(agent.respond(heard, alt_text=heard_hi))
            timings["agent"] = rec["seconds"]
    except Exception as e:  # one bad file must never stop the batch
        rec.update(error=f"{type(e).__name__}: {e}", reply=rec.get("reply") or TROUBLE[lang], decision=rec.get("decision") or "clarify",
                   lang=rec.get("lang") or lang, sources=rec.get("sources", []), retrieved=rec.get("retrieved", []),
                   tool_calls=rec.get("tool_calls", []))
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / path.stem
    t1 = time.time()
    try:
        rec["spoken"] = speak(rec["reply"], rec.get("lang") or "en", stem.with_suffix(".wav"))
        rec["reply_audio"] = str(stem.with_suffix(".wav"))
    except Exception as e:
        rec["error"] = (rec.get("error", "") + f" | TTS {type(e).__name__}: {e}").strip(" |")
    timings["tts"] = round(time.time() - t1, 2)
    rec["seconds"] = round(time.time() - t0, 2)
    stem.with_suffix(".txt").write_text(rec["reply"] + "\n", encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"{path.name}: [{rec['decision']}] {rec['reply'][:100]}" + (f"  !! {rec['error']}" if "error" in rec else ""))
    return rec


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = [handle(f, Agent(), args.output, "") for f in audio_in(args.input)]
    for folder in sorted((d for d in args.input.iterdir() if d.is_dir()), key=natural):
        agent = Agent()  # one conversation = one agent and its state
        records += [handle(f, agent, args.output / folder.name, folder.name) for f in audio_in(folder)]
    with open(args.output / "results.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "conversation", "transcript", "reply", "decision", "sources", "tool_calls", "seconds", "error"])
        for r in records:
            w.writerow([r["file"], r["conversation"], r.get("transcript", ""), r["reply"], r["decision"],
                        " ; ".join(r.get("sources", [])), " ; ".join(r.get("tool_calls", [])), r["seconds"], r.get("error", "")])
    print(f"\n{len(records)} files -> {args.output} (results.csv, plus .txt/.json/.wav per file)")


if __name__ == "__main__":
    main()
