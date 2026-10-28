"""Gnani speech in and out (the only STT/TTS allowed), plus audio conversion and splitting."""
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
import requests
import soundfile as sf
from gnani.stt import GnaniSTTClient
from gnani.tts import AudioConfig, GnaniTTSClient

from src.rules import for_ear, sounds_hindi

CHUNK_SECONDS = 30  # REST STT accepts <= 60 s; Gnani recommends <= 30 s
TTS_MODEL = "timbre-v2.5"
VOICES = {"en": ("Kaveri", "en-IN"), "hi": ("Bhavna", "hi-IN"), "hi-en": ("Poorvi", "hi-en")}
# en-IN writes spoken Hindi numbers as words ("saat hazaar saat sau chialis"); any of these means the
# digits must come from a hi-IN pass, even when the sentence has few other Hindi words
HINDI_NUMBERS = set("""shunya ek teen chaar char paanch panch chhe chheh saat aath nau das gyarah barah bees tees
chalis chaalis pachaas sau hazaar hajaar lakh""".split())
RETRYABLE = {429, 500, 502, 503, 504}

_stt = _tts = None


def _retry(fn, *args, tries=4, **kwargs):
    """The SDK's REST clients don't retry; back off on rate limits and server errors."""
    for i in range(tries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            code = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
            if code not in RETRYABLE or i == tries - 1:
                raise
            time.sleep(2 ** i)


def _chunks(path, tmp):
    """Any audio format -> 16 kHz mono WAV pieces of at most CHUNK_SECONDS."""
    wav = Path(tmp) / "input.wav"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(path), "-ac", "1", "-ar", "16000",
                    "-sample_fmt", "s16", str(wav)], check=True, capture_output=True)
    data, rate = sf.read(wav, dtype="int16")
    step = CHUNK_SECONDS * rate
    pieces = []
    for n, start in enumerate(range(0, len(data), step)):
        piece = Path(tmp) / f"part{n}.wav"
        sf.write(piece, data[start:start + step], rate, subtype="PCM_16")
        pieces.append(piece)
    return pieces, len(data) / rate


def _stt_text(pieces, language):
    texts = []
    for p in pieces:
        try:
            texts.append(_retry(_stt.transcribe, str(p), language_code=language, format="transcribe")["transcript"])
        except Exception as e:
            if getattr(e, "status_code", None) != 400:  # 400 = silent/unusable piece; anything else is real
                raise
    return " ".join(t.strip() for t in texts if t and t.strip())


def transcribe(path):
    """(en-IN transcript, hi-IN transcript or None). Hindi-sounding speech gets a second hi-IN pass,
    because en-IN writes Hindi numbers as words while hi-IN gets them right."""
    global _stt
    _stt = _stt or GnaniSTTClient()
    with tempfile.TemporaryDirectory() as tmp:
        pieces, seconds = _chunks(path, tmp)
        if seconds < 0.3:
            return "", None
        en = _stt_text(pieces, "en-IN")
        words = re.findall(r"[a-z]+", en.lower())
        hindi = sounds_hindi(en) or any(w in HINDI_NUMBERS for w in words)
        return en, (_stt_text(pieces, "hi-IN") or None) if hindi else None


def speak(text, lang, out_path):
    """Synthesize the reply with Gnani TTS; returns the exact text that was spoken."""
    global _tts
    spoken = for_ear(text, "hi" if lang == "hi" else "en")
    voice, language = VOICES.get(lang, VOICES["en"])
    if language == "hi-en":  # the SDK rejects hi-en locally; the documented REST code accepts it
        def post():
            r = requests.post("https://api.vachana.ai/api/v1/tts/inference",
                              headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"]}, timeout=60,
                              json={"text": spoken, "voice": voice, "model": TTS_MODEL, "language": language,
                                    "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                                                     "encoding": "linear_pcm", "container": "wav"}})
            r.raise_for_status()
            return r.content
        Path(out_path).write_bytes(_retry(post))
    else:
        _tts = _tts or GnaniTTSClient()
        _retry(_tts.synthesize, spoken, voice=voice, model=TTS_MODEL, language=language,
               audio_config=AudioConfig(sample_rate=24000), output_file=str(out_path))
    sf.write(out_path, *sf.read(out_path, dtype="int16"))  # Gnani streams 0xFFFFFFFF size fields; store the real ones
    return spoken
