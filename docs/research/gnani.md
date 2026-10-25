# Gnani Vachana STT/TTS: technical brief for the VoiceOps 2026 capstone

Research date: 2026-10-24. Sources: docs.gnani.ai, read through its `llms.txt` index and the `.md` version of each page; PyPI; the GitHub repo and CHANGELOG; and the `gnani-vachana` 0.8.2 wheel source, which I read in memory without installing it. Where a doc page and the SDK source disagree, the **SDK source is treated as the truth for 0.8.2**.

---

## 0. Things that will break you if you follow the docs blindly

| # | Gotcha | Evidence |
|---|---|---|
| 1 | The docs say the SDK default model is `timbre-v2.0` and that leaving out `model` returns 400. In the **0.8.2 source**, `DEFAULT_MODEL = "timbre-v2.5"` and `SUPPORTED_MODELS = {"timbre-v2.5","timbre-v3.0"}`. Passing `timbre-v2.0` raises a local `ValueError`. **Always pass `model=` explicitly.** | `gnani/tts/client.py`; docs python-sdk/introduction |
| 2 | **The SDK rejects `language="hi-en"` (Hinglish) locally with `ValueError`.** `SUPPORTED_TTS_LANGUAGES` is only `auto, hi-IN, en-IN, ta-IN, te-IN, kn-IN, ml-IN, mr-IN, bn-IN, gu-IN, pa-IN`. The raw REST/SSE/WS API does accept `hi-en`. For Hinglish through the SDK, use `voice="Poorvi", language="auto"`. For `hi-en`, use raw `requests`. | wheel source; tts-inference OpenAPI enum |
| 3 | **STT REST in the SDK takes a single language code only.** `_validate_rest_language_code` raises on `"hi-IN,en-IN"` and on `"auto"`. Comma-separated codes were added in 0.7.2 and removed in 0.7.5 ("Code-switching and auto-detect language modes" removed). The server-side `multi_lang_codes` is "not yet exposed through the SDK", and its exact format is **UNVERIFIED**. | CHANGELOG; python-sdk/speech-to-text |
| 4 | **The REST STT and TTS clients have no retry logic.** The docs claim the SDK "handles... retries automatically", but the source contains no retry code (`'retry' in source == False`). Only the Batch client retries: on 429 up to 5 times, honouring `Retry-After`, otherwise 1/2/4/8/16 s; reads also retry on 502/503/504. Wrap REST calls in your own backoff. | wheel source; CHANGELOG 0.8.1 |
| 5 | The SDK's REST STT checks file extensions locally and accepts only `.wav .mp3 .flac .ogg .m4a .aac`. Anything else (`.webm`, `.opus`, `.amr`, `.mp4`) raises `InvalidAudioError` before any network call. Convert those with ffmpeg. | `SUPPORTED_EXTENSIONS` |
| 6 | The SDK's REST STT does **not** expose `bias_list`/`bias_score` (word boosting) or `enable_substitution`/`substitution_map`. To boost a word like "ZentroMart", call the REST API with `requests`. | wheel source vs api/STT/speech-to-text |
| 7 | Voices are tied to a model. Sending a v2.5 voice (e.g. Nalini) with `timbre-v3.0`, or the reverse, returns 400. The SDK also validates this locally with `ValueError`. | available-voices |
| 8 | Audio tags (`<laugh>`, `<pauses>`, …) work only on v3.0. With v2.5 they are stripped. Text that contains only tags returns 400. | available-voices |
| 9 | The Text Normalization guide lists short language codes (`hi`, `en`, `kn`), but the API and SDK use `hi-IN` and similar. The SDK rejects `"hi"`. Use the `-IN` forms. `hinglish` as a language value is rejected. | tts-input-formating |
| 10 | Python version is inconsistent: PyPI says `>=3.9` and CI tests 3.9–3.13, while the API pages say "3.10+". `pipecat-gnani` needs `>=3.11`. **Use 3.11 or 3.12.** | PyPI JSON |
| 11 | `gnani.stt.__version__` reports `"0.8.1"` inside the 0.8.2 wheel. Use `importlib.metadata.version("gnani-vachana")`. Some docstrings are also stale: they claim a default of `timbre-v2.0` / 44100 Hz, but the real `AudioConfig` default is 48000 Hz. | wheel source |
| 12 | The REST STT limit is 60 s (ideal ≤30 s). One OpenAPI description says "Maximum duration: 30 seconds". **Keep chunks ≤30 s.** Going over returns `400 INVALID_REQUEST_ERROR "Audio duration exceeds maximum limit of 60 seconds, while the ideal duration is 30 seconds."` | api/STT/speech-to-text OpenAPI |
| 13 | Batch language support is inconsistent. The REST page and the Batch intro say Batch does **not** support `gu-IN`/`pa-IN`, but both list them in their tables and the SDK accepts them. The call-analytics guide lists `hi-en` and `bn-BD` for Batch, but the SDK would reject them. **UNVERIFIED.** This doesn't affect EN/HI. | docs |
| 14 | Invalid `bias_list` input fails silently: you still get a 200 with no boosting. | api/STT/speech-to-text |
| 15 | When credits run out you get a `403 FORBIDDEN` "...Check your API key, organization status, or available credits.", not a 402. | OpenAPI examples |

---

## 1. Install, version, Python

- `pip install gnani-vachana` (or `uv add gnani-vachana`). The import name is `gnani` (`from gnani.stt import ...`, `from gnani.tts import ...`).
- **Latest version is 0.8.2**, released 2026-10-22. Recent releases: 0.7.1 … 0.7.9, 0.8.0, 0.8.1, 0.8.2. Pin `gnani-vachana==0.8.2`. Batch needs ≥0.8.1.
- `requires_python >=3.9`. Classifiers cover 3.9–3.13. Dependencies are only `requests>=2.28.0` and `websockets>=12.0`. MIT license, "4 - Beta".
- Repo: https://github.com/Gnani-AI-Mintlify/gnani-vachana. It has 1 star, 0 open issues and a `.env.example` containing `GNANI_API_KEY=`.
- Auth uses a single key in the `X-API-Key-ID` header. Every client reads `GNANI_API_KEY`. If no key is found, the constructor raises `AuthenticationError` before any network call. `organization_id`/`user_id` were removed in 0.7.x.
- Base URL is `https://api.vachana.ai`. Every client takes `base_url=` (https is converted to wss for the streaming clients).
- Optional header `X-API-Request-ID`: the SDK generates one automatically, or you pass `request_id=`. It is echoed back in STT REST responses. Log it.

## 2. Client constructors and full method signatures (from the 0.8.2 source)

### STT (`gnani.stt`)

```python
GnaniSTTClient(api_key: str|None=None, *, base_url="https://api.vachana.ai", timeout: int=60)
  .transcribe(audio: str|Path|BinaryIO, language_code="en-IN", *, format="verbatim",
              itn_native_numerals=False, request_id=None) -> dict
  .transcribe_bytes(audio_bytes: bytes, filename="audio.wav", language_code="en-IN", *,
              format="verbatim", itn_native_numerals=False, request_id=None) -> dict
  GnaniSTTClient.supported_languages() -> dict[str,str]        # staticmethod

GnaniSTTStreamClient(api_key=None, language_code="en-IN", *, sample_rate=16000,
                     base_url=..., format="verbatim", itn_native_numerals=False)   # async
  await .connect(request_id=None) -> StreamConnectedEvent
  await .send_audio(chunk: bytes)                 # exactly 1024-byte frames
  await .close() -> list[StreamTranscriptEvent]
  await .stream_audio(audio_source: AsyncIterator[bytes]|BinaryIO, *, on_transcript=None,
        on_processing=None, on_error=None, chunk_size=1024, realtime_pace=True) -> list[StreamTranscriptEvent]
  async for ev in stream / .events();  props: is_connected, connected_config, transcripts
  async with GnaniSTTStreamClient(...) as s: ...   # ping_interval=20, ping_timeout=20, close_timeout=10

GnaniSTTBatchClient(api_key=None, *, base_url=..., timeout=60, upload_timeout=600)
  .transcribe(files, language_code="en-IN", *, timeout=None, progress=True,
              raise_on_failure=True, **options) -> BatchResult
  .create_job(files, language_code="en-IN", *, model="gnani-prisma-v2.5", diarization=False,
              speakers=None, multi_channel=False, denoise=False, bias_words=None,
              bias_score=None, callback_url=None, start=True, request_id=None) -> BatchJob
  .get_job(job_id) -> BatchJob ; .list_jobs(*, status=None, limit=20) -> Iterator[BatchJob]
  BatchJob: .id .status .percent .refresh() .start() .cancel(reason) .files(status=None) .save(dir, text_files=False)
            .wait(*, timeout=None, poll_interval=10.0, max_poll_interval=30.0, progress=False,
                  on_progress=None, raise_on_failure=True)
  BatchFile: .name .status .ok .duration .error .text .segments[BatchSegment(start,end,text,speaker)] .transcript(dict)
  BatchResult: iterable/indexable, .job .files .failed .text .save(dir, text_files=False)
AsyncGnaniSTTBatchClient  # same methods, awaited; `await job.files(load=True)`
```

- REST response shape: `{"success": true, "request_id": "...", "timestamp": "YYYYMMDD_HHMMSS.mmm", "transcript": "..."}`. The quick-start sample also shows `"model": "gnani-prisma-v2.5"`. According to the docstring, `processing_time` and `end_to_end_latency` are also present (**UNVERIFIED** live).
- Stream events are typed dataclasses, each with a `.raw` dict:
  - `StreamConnectedEvent(message, timestamp, sample_rate, chunk_size)`
  - `StreamProcessingEvent(timestamp)`
  - `StreamTranscriptEvent(text, audio_duration_ms, segment_id, segment_index, latency, timestamp)`
  - `StreamErrorEvent(message, timestamp)`
- Exceptions all inherit from `GnaniSTTError`: `AuthenticationError`, `APIError(.status_code, .body)`, `InvalidAudioError`, `StreamConnectionError`, `StreamClosedError`, `StreamError`, `BatchJobFailedError(job_id, status, reason)`, `BatchTimeoutError(job_id, timeout)`. Invalid parameters raise `ValueError`.
- Exported constants: `SUPPORTED_LANGUAGES`, `STREAM_SUPPORTED_LANGUAGES`, `STREAM_SUPPORTED_SAMPLE_RATES=(8000,16000,44100,48000)`, `STREAM_CHUNK_SAMPLES=512`, `STREAM_CHUNK_BYTES=1024`.

### TTS (`gnani.tts`)

```python
GnaniTTSClient(api_key=None, *, base_url=..., timeout: int=60)                 # REST  POST /api/v1/tts/inference
  .synthesize(text, voice="Pranav", *, model="timbre-v2.5", language=None, speed=None,
              audio_config: AudioConfig|None=None, speaker_embedding=None,
              output_file: str|Path|None=None, request_id=None) -> bytes       # writes file + returns bytes
  GnaniTTSClient.supported_voices(model="timbre-v2.5") -> list[str]

GnaniTTSStreamClient(api_key=None, *, base_url=..., timeout=60)                 # SSE  POST /api/v1/tts/sse (sync)
  .synthesize_stream(text, voice="Pranav", *, model, language, speed, audio_config,
                     speaker_embedding, request_id) -> Iterator[bytes]         # raw PCM chunks, no WAV header
  .synthesize(..., output_file=None, ...) -> bytes                              # adds RIFF header for linear_pcm/wav

GnaniTTSRealtimeClient(api_key=None, *, base_url=...)                           # WS wss://api.vachana.ai/api/v1/tts (async)
  async for chunk in .synthesize(...) -> AsyncIterator[bytes]
  async for ev in .synthesize_events(...)  -> TTSStartEvent(request_id,message) |
                                              TTSAudioChunkEvent(data,chunk_index,is_final) |
                                              TTSCompletedEvent(request_id,total_chunks)
  await .synthesize_and_collect(..., output_file=None) -> bytes
  # one WebSocket per call; `async with` does not pool connections

AudioConfig(sample_rate=48000, encoding="linear_pcm", num_channels=1, sample_width=2,
            container="wav", bitrate=None)
SpeakerEmbedding(embedding: str, shape: list[int], dtype="torch.bfloat16")      # voice cloning
```

- The SDK sends `speed=1.0` by default for Timbre models. It sends `language` only if you set it. Because the API marks `language` as "required", **always pass `language`** (whether the server rejects a missing value is **UNVERIFIED**).
- TTS exceptions: `GnaniTTSError` is the root, with `AuthenticationError`, `APIError`, `StreamConnectionError`, `StreamClosedError`, `StreamError`. `ValueError` (bad voice, model, language, speed, sample_rate, container or bitrate) is raised locally.

## 3. STT input constraints

| | REST `POST /stt/v3` | Realtime `wss://api.vachana.ai/stt/v3/stream` | Batch `/stt/v3/batch/jobs` |
|---|---|---|---|
| Formats | WAV, MP3, OGG, FLAC, AAC, M4A | raw PCM s16le only, mono, **exactly 1024-byte frames** at real-time pace (32 ms per frame at 16 kHz, 64 ms at 8 kHz) | .wav .mp3 .mp4 .flac .ogg .opus .m4a .aac .webm .amr, .zip |
| Sample rate / channels | auto-converted to 16 kHz mono; mono or stereo accepted; quick start says 8–44.1 kHz | `x-sample-rate` must be 8000, 16000, 44100 or 48000 | — |
| Duration | **≤60 s (ideal ≤30 s)** | session capped at **15 min**; one language per session | 0.1 s – **4 h** per file; ≤5,000 segments |
| Size | no byte limit documented (**UNVERIFIED**) | — | upload 10 MB per file, 100 files per job, ZIP 50 MB (200 MB decompressed); cloud_storage has no byte cap |
| Language | one code | one code (`lang_code` header) | one code, or **up to 3 comma-separated** for per-file language ID (first is the fallback; resolved `language_code` is returned in the transcript JSON). SDK also allows `"auto"` alone (server behaviour **UNVERIFIED**) |
| ITN | `format="transcribe"`, **hi-IN and en-IN only** | `x-format: transcribe` | **not supported** (verbatim only) |
| Extras | `bias_list` (≤100 single words, letters only) + `bias_score` ∈ {0, 0.5, 1, 1.5, 2}; `substitution_map` (≤10 rules); raw API only | VAD headers `x-vad-threshold` (0.7), `x-min-silence-ms` (500), `x-min-speech-ms` (100), `x-min-segment-ms` (120), `x-max-speech-s`; mid-session `update_settings` for bias and substitution | diarization (`speakers` 1–8), denoise, `bias_words`, `callback_url`; poll ≥10 s (30 s for 100+ files); `transcript_url` expires after 1 h |

**Handling audio longer than 60 s:**
- **(a)** Split into ≤30 s chunks, ideally on silence, then call REST on each and join the text. This is the simplest option and keeps latency low.
- **(b)** Use `GnaniSTTBatchClient`, which handles up to 4 h but adds at least 10 s of polling per job.
- **(c)** Stream 16 kHz PCM through `stream_audio()`. Real-time pacing means a 2-minute file takes about 2 minutes. `realtime_pace=False` degrades VAD.

## 4. Languages, scripts, Hinglish, auto-detection

- **STT codes** (Prisma v2.5): `bn-IN en-IN gu-IN hi-IN kn-IN ml-IN mr-IN pa-IN ta-IN te-IN`.
  - `hi-IN` outputs **Devanagari**.
  - `en-IN` "Accepts English-Hindi mixed audio and generates output in English (Latin script)", so it is the natural choice for Hinglish.
  - There is no Hinglish STT code on REST or Realtime. There is no auto-detect in the SDK's REST or Realtime clients.
  - Auto/multi-language options: Batch only (≤3 codes per file), or the undocumented REST `multi_lang_codes` (**UNVERIFIED**).
  - The ITN examples show code-mixed handling: "कल थ्री फिफ्टी पीएम को पाँच सौ रुपये transfer करना है" becomes "कल 15:50 को ₹500 transfer करना है".
- **Practical language strategy (my inference, not documented):** for each test file, either (1) run REST with `en-IN` and `hi-IN` in parallel (double the credits) and let the LLM or a script/text heuristic pick, or (2) in the offline batch command, use Batch with `language_code="hi-IN,en-IN"` and read the resolved `language_code`. The REST response has no confidence score.
- **TTS `language`** (API): `auto, hi-IN, en-IN, hi-en, ta-IN, te-IN, kn-IN, ml-IN, mr-IN, pa-IN, bn-IN, gu-IN`. The SDK excludes `hi-en`.
  - How `auto` resolves: Devanagari resolves to Hindi. Devanagari mixed with Latin resolves to Hinglish. **Latin-only text resolves to English**, which matters for romanized Hinglish. So write Hinglish replies with the Hindi words in Devanagari and the English words in Latin when you use `auto` (inference based on the doc's table).

## 5. TTS models and voices

| Model | Voices | Notes |
|---|---|---|
| `timbre-v2.5` | 42; each has one preferred language | supports `language` and `speed` (0.85–1.15; the API also accepts the strings "slow"=0.85, "medium"=1.0, "fast"=1.15); no audio tags |
| `timbre-v3.0` | 13; **every voice speaks all 10 languages** | supports `language`, `speed`, and the audio tags `<coughs> <excited> <exhales> <giggle> <laugh> <pauses> <shouting> <sigh> <slow> <sniffles> <whispers> <yawns> <clears throat>`; the SDK accepts it (`TIMBRE_V30_VOICES`) |
| `timbre-v2.0` | deprecated or removed; the SDK rejects it | — |

**timbre-v2.5 voices by preferred language:**
- en-IN: Kaveri, Trupti, Devika, Pranav, Shlok, Girish
- hi-IN: Nalini, Bhavna, Yashvi, Urmila, Jwala, Chitra, Ambuja, Deepak, Roopesh, Vikrant, Hemraj, Jalaj, Omkar
- Hinglish (`hi-en`, or `auto` in the SDK): **Poorvi** (only one)
- ta-IN: Asmita, Trisha, Brinda, Vedika, Noopur
- te-IN: Suhana, Lehara, Lavanya, Yukti, Varuni
- kn-IN: Saanvi, Kavin
- ml-IN: Reshma, Riyaan
- mr-IN: Zahira, Ishaan
- bn-IN: Kirra, Dhruva
- gu-IN: Falak, Veera
- pa-IN: Mehuli, Zayan

Voices whose catalog descriptions fit customer support:
- English: Kaveri (F, "Firm voice for customer support"), Devika (F, authoritative support), Pranav (M, friendly support)
- Hindi: Bhavna (F, "Friendly voice for customer support"), Chitra (F, customer care), Omkar (M, customer support)
- Hinglish: Poorvi (F)

**timbre-v3.0 voices:**
- Female: Shivani, Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika
- Male: Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad
- Shivani is described as "Warm, patient, empathy-first voice for inbound customer support". One v3.0 voice in all three languages gives a consistent persona, which may help the voice-UX score. Check whether the brief allows v3.0 (its example uses v2.5 + Kaveri).
- The playground is at https://app.gnani.ai/voice/text-to-speech (login required).

## 6. TTS output formats

| container | encoding | sample rates | notes |
|---|---|---|---|
| `wav` (default) | `linear_pcm` | 8000, 16000, 22050, 24000, 44100, **48000 (default)** | RIFF; 16-bit mono by default; `audio/wav` |
| `mp3` | — | same | `bitrate` 32k/64k/96k/128k(default)/192k |
| `raw` | `linear_pcm` | same | headerless PCM |
| `ogg` / `raw`+`oggopus` | oggopus | same | arrives as **one chunk** on SSE/WS (not streamable) |
| `mulaw` / `alaw` | — | forced to 8000 | G.711 telephony |

The SSE and WS wire formats both carry base64 `audio` inside `{chunk_index, audio, is_final}` messages. The SDK decodes them for you. **The maximum text length per request is not documented (UNVERIFIED)**, so keep replies short and split them by sentence for streaming.

## 7. Text normalization (TTS input)

TN runs automatically. Rules relevant to ZentroMart:
- **Currency:** `₹599` and `Rs 500` read as rupees. `₹4,312.50` reads as rupees plus paise. Lakh/crore grouping is honoured. The rupee word is localized (रुपये in Hindi).
- **Dates:** `DD/MM/YYYY`, `DD-MM-YYYY` and `25 Jun 2026` are read in full. **`23/06` without a year is read as a fraction**, so always include the year.
- **Times:** `5:30 PM` reads as "five thirty P M". `20:00` reads as "eight P M".
- **Digit-by-digit triggers:** words such as `account, OTP, card, PIN, Aadhaar, PAN` near a number; any run of 6+ digits; numbers of exactly 4, 6, 10, 12 or 16 digits.
  - `#12345` and `Invoice #12345` read as "Invoice number one two three four five".
  - English compresses repeats (`880044` becomes "double eight double zero double four"); other languages spell each digit.
  - **References of 14+ digits are read as a raw string**, so add spaces or hyphens.
  - Duration words (`minutes`, `hours`, `days`) force a quantity reading.
- **Phone numbers** are grouped 3-3-4. Masked numbers like `****4821` read only the visible digits.
- **Alphanumeric order IDs (e.g. `ZM-48213`):** there is no explicit rule. Reading behaviour is **UNVERIFIED**, so pre-format the ID (spaced letters plus grouped digits) and listen-test it.
  - The REST TTS page contradicts the TN guide. It says "Pass numbers, dates, and currency as spoken words to avoid mispronunciations", while the TN guide says they are "handled automatically". For key fields, normalize them yourself.
- Abbreviations like OTP, EMI, UPI, KYC, GST and SMS are spelled out letter by letter.
- "Gnani" is pronounced "Gyaanee". For custom brand pronunciations (e.g. "ZentroMart") you have to contact Gnani.
- **STT side:** with `format="transcribe"` (hi-IN and en-IN only), a 10-digit stream becomes a phone number, a 6-digit stream a PIN, and "double/डबल" prefixes are expanded. Order IDs of other lengths are not covered (**UNVERIFIED**). Add your own regex step to turn spoken digits (English and Hindi words) into numbers before calling `lookup_order`.

## 8. Errors, rate limits, retries, timeouts

- **HTTP errors** use the body `{"success": false, "error": {"type", "message"}}`:
  - 400 `INVALID_REQUEST_ERROR`
  - 401 missing or invalid key
  - 403 `FORBIDDEN` (key, organization or credits)
  - 429 `RATE_LIMIT_ERROR`
  - 500 `API_ERROR` (retry with backoff)
  - 503 `SERVICE_UNAVAILABLE`
  - Batch adds codes such as `AUDIO_TOO_LONG`, `UNSUPPORTED_LANGUAGE`, `JOB_NOT_FOUND`, `TOO_MANY_FILES`, and "Empty transcript after 3 retries" for silent or tone-only audio.
- **Rate-limit numbers** (requests per second, concurrency) are **not published (UNVERIFIED)**. The docs only say "the API is rate limited".
- **Timeouts:** the REST and SSE clients default to `timeout=60` s via requests. Batch uploads use `upload_timeout=600`. The STT WebSocket pings every 20 s.
- **Retries:** only the Batch client retries. Implement your own retry with backoff on 429/500/503 for REST STT and TTS.
- A path containing `../` in the multipart filename is blocked by a Cloudflare WAF with a 403 HTML page. The SDK sends only the basename.

## 9. Pricing and credits

- **Pricing is not public.** Gnani's own blog says "Gnani AI does not publish pricing."
- https://app.gnani.ai/voice redirects to a Keycloak login at iamportal.gnani.site. You can register with email, Google or Microsoft. The free-credit amount is not visible without logging in (**UNVERIFIED**). How credits convert to minutes or characters is also **UNVERIFIED**.
- Gnani is running a separate programme, the "Great Indian AI Internship Challenge 2026": registration is free, each registrant gets **5,000 programme credits** on app.gnani.ai/voice, and submissions close **Nov 10**. Registration: https://www.gnani.ai/great-indian-ai-internship-registration-form. It recommends Prisma v2.5, Timbre v2.5 and an open-weights LLM, "Evon v3.3". This could be an optional extra for the team.
- Support: Discord https://discord.gg/aECcvtABpq, email hello-inya@gnani.site, and support@gnani.ai (the PyPI author address).

## 10. Integrations (optional, for a live voice demo)

- `pipecat-gnani` 0.5.12: needs Python ≥3.11 and depends on `gnani-vachana>=0.7.9,<1.0`. Provides `GnaniSTTService` (WebSocket), `GnaniHttpSTTService` (needs VAD), `GnaniTTSService` (WebSocket), `GnaniSSETTSService` and `GnaniHttpTTSService`.
- `livekit-plugins-gnani` 1.8.9: needs Python ≥3.10. Provides `livekit.plugins.gnani.STT` / `TTS` (`synthesize_method="sse"`).

## 11. Minimal working code (SDK 0.8.2)

```python
# common.py — pip install gnani-vachana==0.8.2 ; export GNANI_API_KEY=...
import time
from gnani.stt import GnaniSTTClient, APIError as STTAPIError
from gnani.tts import GnaniTTSClient

stt, tts = GnaniSTTClient(), GnaniTTSClient()

def retry(fn, *a, tries=4, **kw):  # SDK REST clients don't retry
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:
            if getattr(e, "status_code", None) not in (429, 500, 503) or i == tries - 1:
                raise
            time.sleep(2 ** i)
```

**Batch-transcribe a folder of test audio (REST loop; best for ≤30–60 s clips):**
```python
import json, pathlib
EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}   # SDK whitelist; convert others with ffmpeg
out = {p.name: retry(stt.transcribe, p, language_code="en-IN", format="transcribe")["transcript"]
       for p in sorted(pathlib.Path("test_audio").iterdir()) if p.suffix.lower() in EXTS}
pathlib.Path("transcripts.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
```

**Same folder through Batch (handles long files plus per-file EN/HI language ID; poll latency ≥10 s):**
```python
from gnani.stt import GnaniSTTBatchClient
res = GnaniSTTBatchClient().transcribe("test_audio/", language_code="hi-IN,en-IN")  # first = fallback
for f in res:
    print(f.name, f.transcript.get("language_code") if f.ok else "-", f.text if f.ok else f.error)
```

**Pre-splitting audio over 60 s** (ffmpeg; this cuts at fixed points, so prefer silence-based splitting):
`ffmpeg -i long.mp3 -ac 1 -ar 16000 -f segment -segment_time 30 chunk_%03d.wav`

**Hindi STT (Devanagari, digits normalized by ITN):**
```python
text = retry(stt.transcribe, "hindi.wav", language_code="hi-IN", format="transcribe")["transcript"]
# "पाँच हज़ार रुपये" -> "₹5,000"; itn_native_numerals=True -> "₹५,०००"
```

**English STT with "ZentroMart" word boosting (raw REST, because the SDK doesn't expose it):**
```python
import os, requests
r = requests.post("https://api.vachana.ai/stt/v3", headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"]},
    files={"audio_file": open("q.wav", "rb")},
    data={"language_code": "en-IN", "format": "verbatim", "bias_list": '["ZentroMart"]', "bias_score": "1.0"},
    timeout=60)
r.raise_for_status(); print(r.json()["transcript"])
```

**TTS reply to WAV (the brief's call; valid on 0.8.2):**
```python
retry(tts.synthesize, reply, voice="Kaveri", model="timbre-v2.5", language="en-IN", output_file="reply.wav")
# default AudioConfig = 48 kHz 16-bit mono WAV; smaller: audio_config=AudioConfig(sample_rate=24000)
# Hindi: voice="Bhavna" (or Nalini/Chitra), language="hi-IN"
```

**Hinglish TTS:**
```python
# SDK: hi-en is rejected locally -> use Poorvi + auto with mixed Devanagari/Latin text
retry(tts.synthesize, "आपका order कल deliver हो जाएगा, refund 5 से 7 दिन में आएगा।",
      voice="Poorvi", model="timbre-v2.5", language="auto", output_file="reply_hinglish.wav")

# Raw REST with the documented hi-en code
r = requests.post("https://api.vachana.ai/api/v1/tts/inference",
    headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"]},
    json={"text": "Aapka order kal deliver ho jayega.", "voice": "Poorvi", "model": "timbre-v2.5",
          "language": "hi-en", "speed": 1.0,
          "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                           "encoding": "linear_pcm", "container": "wav"}}, timeout=60)
r.raise_for_status(); open("reply_hinglish.wav", "wb").write(r.content)
```

**Low-latency streaming (for the voice-UX demo):**
```python
import asyncio
from gnani.tts import GnaniTTSRealtimeClient
async def speak(t):
    async with GnaniTTSRealtimeClient() as c:
        async for chunk in c.synthesize(t, voice="Kaveri", model="timbre-v2.5", language="en-IN"):
            player.write(chunk)  # raw PCM 48k s16le mono
```

## 12. Not verified (needs a live API key)

- Free-credit amount and pricing.
- Numeric rate limits.
- REST STT file-size limit.
- The `multi_lang_codes` field format.
- Whether Batch `"auto"` and `hi-en` actually work on the server.
- How alphanumeric order IDs are read by TTS and normalized by STT ITN.
- What happens when TTS `language` is omitted.
- Maximum TTS text length.
- How well `en-IN` STT handles pure-Hindi speech.
- Whether `timbre-v3.0` is allowed under the capstone rules.

## Sources

- https://docs.gnani.ai/llms.txt (index)
- https://docs.gnani.ai/api/introduction/introduction.md
- https://docs.gnani.ai/api/introduction/quick-start.md
- https://docs.gnani.ai/python-sdk/introduction.md, /python-sdk/speech-to-text.md, /python-sdk/speech-to-text-batch.md, /python-sdk/text-to-speech.md
- https://docs.gnani.ai/api/STT/speech-to-text.md, /api/STT/stt-websocket.md, /api/STTBatch/Introduction.md
- https://docs.gnani.ai/api/TTS/available-voices.md, /api/TTS/tts-inference.md, /api/TTS/tts-sse.md, /api/TTS/tts-websocket.md, /api/TTS/tts-audio-tags.md, /api/TTS/tts-input-formating.md
- https://docs.gnani.ai/api/use-cases/call-analytics.md, /pipecat/introduction.md, /livekit/introduction.md
- https://pypi.org/project/gnani-vachana/ and https://pypi.org/pypi/gnani-vachana/json (wheel 0.8.2 source: `gnani/stt/client.py`, `gnani/stt/batch.py`, `gnani/tts/client.py`)
- https://github.com/Gnani-AI-Mintlify/gnani-vachana (CHANGELOG.md, .env.example)
- https://pypi.org/pypi/pipecat-gnani/json, https://pypi.org/pypi/livekit-plugins-gnani/json
- https://app.gnani.ai/voice (login page only)
- https://www.gnani.ai/resources/blogs/great-indian-ai-internship-challenge-2026
- https://www.gnani.ai/resources/blogs/how-gnani-ai-is-revolutionizing-cx-with-generative-ai (the "does not publish pricing" quote)