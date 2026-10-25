# VoiceOps 2026 — ZentroMart voice support agent

A customer-support agent for the fictional store ZentroMart that answers from company documents, holds a verified multi-turn conversation, and takes phone-style audio in and out through **Gnani** speech (the only STT/TTS used).

```
audio ─► Gnani STT (en-IN, + hi-IN for Hindi speech) ─► agent ─► Gnani TTS ─► reply.wav
                                                         │
     LLM call 1: understand (English search query, language, products, dates, flags)
     code: verification state machine · lookup_order / create_ticket · date maths · escalation rules
     retrieval: BM25 + multilingual embeddings over 84 KB sections, fused (RRF), labelled by authority
     LLM call 2: compose (decision, reply, evidence IDs)  ─►  code guards (no fake actions, no leaks)
```

The LLM only understands and phrases. Dates, return windows, refund timelines, verification retries and escalation thresholds are deterministic Python, unit-tested against the practice gold answers, and unverified order data never reaches the model.

## Setup

Python 3.11 or 3.12. **On Windows, clone into a short path** (e.g. `C:\voiceops`): torch's installed file paths are long, and without [long-path support](https://pip.pypa.io/warnings/enable-long-paths) `pip install` fails inside deep folders.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; on macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt   # `python -m pip` also works where Windows blocks the pip.exe launcher
cp .env.example .env              # then fill in the keys
```

`.env` needs:
- `GNANI_API_KEY` — from app.gnani.ai/voice → API Keys.
- `LLM_API_KEY` — a Gemini key (aistudio.google.com/apikey); the default model is `gemini-3.1-flash-lite`. Any OpenAI-compatible endpoint works via `LLM_BASE_URL` / `LLM_MODEL`, or set `LLM_PROVIDER=anthropic` with `ANTHROPIC_API_KEY`.
- `DATASET_DIR` — path to the extracted `Capstone_Project_Dataset_FTTT_2026` folder (default: inside this repo). The dataset is not committed.

The first run downloads the `intfloat/multilingual-e5-small` embedding model (~470 MB) from Hugging Face.

## Run on a folder of audio

```bash
python run.py --input path/to/audio --output outputs
```

- Audio files directly in the input folder are treated as separate calls. Each **sub-folder is one conversation**, its files played to the same agent in natural order (`turn1`, `turn2`, …).
- Any common format works (wav, mp3, m4a, ogg, flac, webm, …); audio is converted to 16 kHz mono and split into ≤30 s pieces for Gnani STT.
- For every input file the output folder gets `<name>.wav` (spoken reply), `<name>.txt` (reply text) and `<name>.json` (transcripts, reply, decision, the cited section IDs, the retrieved chunks with text and scores, tool calls, timings), plus one `results.csv` for the whole run. A failing file is recorded and the batch continues.

## Live demo

```bash
python app.py        # open http://127.0.0.1:7860, record or type a question
```

Shows the transcript, the spoken reply, and the decision, cited sections, tool calls and verification state for each turn.

## Evaluate

```bash
python -m pytest tests                              # date / window / escalation / ASR rules vs gold
python eval/evaluate.py --mode retrieval [--asr]    # section-ID Recall@k, no LLM
python eval/evaluate.py --mode baseline             # Step 1: prompt only
python eval/evaluate.py --mode rag                  # Step 2: + retrieval
python eval/evaluate.py --mode full [--asr]         # full agent on single questions
python eval/evaluate.py --mode conversations        # multi-turn, incl. exact tool calls
python eval/make_audio.py --out test_audio --questions PQ0003 --conversations PC002   # Gnani-TTS test audio
```

Results are written to `eval/results/` as CSV + markdown tables. LLM responses are cached in `.cache/` so re-runs are free and repeatable.

## Layout

| Path | What |
|---|---|
| `run.py` | Batch voice command |
| `app.py` | Gradio live demo |
| `src/agent.py` | Conversation state, verification, tools, LLM calls, guards |
| `src/kb.py` | Section parser and hybrid retrieval |
| `src/rules.py` | Business days, return windows, refund timelines, escalation flags, ASR normaliser |
| `src/voice.py` | Gnani STT/TTS, audio conversion |
| `eval/` | Practice-set scorer and test-audio generator |
| `tests/` | Rule tests against the practice gold |
