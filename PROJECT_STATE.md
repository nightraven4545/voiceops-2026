# Project state — VoiceOps 2026 capstone

> **Handoff file.** Read this first in any new chat. Update it (and commit) after every milestone and before ending a session.
> Last updated: **25 Oct 2026, 13:00 IST** · latest commit on `origin/main` (private GitHub repo).

## ▶ Handoff — start here
**Where things stand.** The agent is built, evaluated (full agent 96%, conversations 93%, tool calls 100% exact), documented, and pushed. The report PDF and `sample_outputs/` are done. A clean clone installs and runs (44/44 tests). What's left is mostly finishing and submitting.

**In flight:** nothing.
- The clean-clone check **passed** at 12:48 IST on 25 Oct: 13/13 files with **live** LLM calls (24 fresh responses, 0 errors), and PC002 made exactly the gold tool calls including `create_ticket()`.
- Live latency on the free tier: median 20.9 s per voice turn (9–49 s).
- `%USERPROFILE%\vofresh`, including its `.env` copy of the keys, has been **deleted**.

**Next actions, in order (deadline 26 Oct 2026):**
1. ~~Clean-clone LLM check + delete `vofresh`~~: done (see above).
2. **PC021 by voice (Hindi failed verification), after 12:30 IST, ~10 LLM calls:**
   - Run `run.py` on `test_audio/PC021`. Expect: turns in Devanagari Hindi; turn 3 `lookup_order(order_id=77461439, verification_value=1266)` → clarify; turn 4 → refuse.
   - Then add it to `sample_outputs/`: copy the inputs, rerun into `replies`, add a README row. Commit.
3. **Demo video, recorded by the user:** ≤2 min, `python app.py` in Chrome, record with Win+Alt+R (Xbox Game Bar) or Clipchamp. Suggested script:
   1. English: "How long does a refund to UPI take?" → follow-up "And if I paid by card?"
   2. Hinglish order flow: give order ID 8978 2837, then last 4 digits 4533, then "TV damaged, replacement approve kar do" → ticket + handover
   3. "Is there a student discount?" → "I don't have that information"

   Keep the details panel (sources, tool calls) visible. Save as `demo.mp4`.
4. **Ask the organizers on Discord:**
   - whose LLM key runs the test (free tier ≈ 500 calls/day; a 200-file run needs ≈ 400)
   - how multi-turn audio is delivered (we treat each sub-folder as one conversation)
   - output schema
   - retrieval metric
   - deadline time
5. **Optional, only with spare time and quota:**
   - a post-check that "must state" computed facts (refund timing, RRN) appear in the reply
   - softer abstention on "what if I'm not home?"

   Each change needs an eval rerun (full + conversations ≈ 300 calls), so don't start this on submission day.
6. **Submission:**
   - make the repo public: `gh repo edit nightraven4545/voiceops-2026 --visibility public --accept-visibility-change-consequences`
   - build `<team>_voiceops.zip` with `README.md`, `.env.example`, `requirements.txt`, `run.py`, `src/`, `report.pdf` (copied from `report/`), `demo.mp4`, `sample_outputs/`
   - leave out `.env`, any venv, the dataset copy, `.cache`, `outputs/` and `test_audio/`
   - put the public repo URL in the submission
7. **After submission:** rotate the Gnani and Gemini keys; both were pasted in chat.

**Don't redo or undo:**
- the model choice (Gemini 3.1 free; the $100 is Claude Code cloud credit, not API)
- the per-model results folders
- the rejected superseded-section down-weighting
- the gold-aligned decisions: unanswerable → `answer`; compensation → `refuse`

**Budget:** ~500 Gemini calls/day per model, reset 12:30 IST. A full eval ≈ 450 calls. Cached answers are free.

## Goal and deadline
IIT-G C&A × Gnani.ai "VoiceOps 2026": a voice customer-support agent for the fictional store ZentroMart. Brief: `C:\Users\shres\OneDrive\Documents\capstone_AI_ML\6ad64c83eae85_voiceops_2026_capstone_brief.pdf`.
**Final submission closes 26 Oct 2026** (course site; time of day unknown).

Rubric (100):
- grounded answers 25
- retrieval 15
- conversation 20
- own evaluation 10
- voice end-to-end 10
- voice experience 10
- report + demo 10

Hard rules:
- Gnani is the only STT/TTS, even as a fallback (anything else disqualifies)
- no hardcoded answers
- test answers come from the agent

Submission:
- public GitHub repo with a README
- `.env.example`
- one run command over a folder of audio
- report ≤4 pages
- demo video ≤2 min
- `sample_outputs/`

## Status
| Area | State |
|---|---|
| Agent (`src/`), batch runner (`run.py`), demo (`app.py`) | Built and working |
| Rule + agent tests | 44 passing (`python -m pytest tests`) |
| Evaluation on `gemini-3.1-flash-lite` | **Complete**, every row filled |
| Voice end to end | 17/17 files processed, batch never stops; Hindi digits verified live (PC021). Hindi-language fix verified on turn 2; turns 3–4 hit the daily quota on the retest |
| Report | `report/report.md` → `report/report.pdf` (3 pages, A4). Rebuild: `python report/build_pdf.py` (needs `pip install markdown`; uses headless Chrome, since Edge on this PC writes nothing) |
| Sample outputs | `sample_outputs/`: 13 files (8 questions, PC002 conversation, silence), replayed from cached LLM answers with live calls blocked; 0 errors. PC021 to be added after a live rerun |
| Git | **Private** repo https://github.com/nightraven4545/voiceops-2026 (`main`, pushed 25 Oct). Author `Shreshtha <77679539+nightraven4545@users.noreply.github.com>`, no AI trailers. Make it public only at submission: `gh repo edit nightraven4545/voiceops-2026 --visibility public --accept-visibility-change-consequences` |

## Results (practice set, `eval/results/<model>/`)
| Model | Step 1 baseline | Step 2 RAG | Full agent | Full, `asr_text` | Conversations (turns) | Tool calls |
|---|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` (**submission**) | 15% | 83% | **96%** | **96%** | **93%** (96/96 turns), decisions 100% | 100% exact |
| `gemini-3.5-flash-lite` (earlier) | 21% | 67%* | 92% | — | incomplete (quota) | 100% exact |

\*3.5's Step 2 ran before the prompt fixes.

Retrieval Recall@5, using the cached 3.1 rewrites:

| Query | Recall@5 | Hindi |
|---|---|---|
| raw customer text | 0.68 | 0.43 |
| English rewrite + raw at half weight | **0.90** | 0.86 |
| same, on noisy `asr_text` | 0.85 | — |

Remaining failures:
- **Conversations:**
  - fact left unstated: PC019/PC020 refuse-at-door "7–10 days", PC010 RRN
  - over-cautious abstention: PC011/PC012 "what if I'm not home"
  - Hindi synonyms the strict scorer misses: PC009, PC016
- **Single questions:** PQ0053 invented an answer; PQ0058 asked "which colour?" unnecessarily.

## Key decisions (and why)
- **Agent LLM = Gemini `gemini-3.1-flash-lite`, free tier, via the OpenAI-compatible endpoint.**
  - The user chose free Gemini.
  - The $100 Claude credits are **Claude Code cloud-session credits** (expire 5 Nov), not API credits: they can't pay for the agent's calls.
  - Claude still works through `LLM_PROVIDER=anthropic` if an API key is added.
- Architecture: the LLM only *understands* (call 1: English query, language, products, dates, flags) and *phrases* (call 2). Everything else is code:
  - verification state machine
  - tools
  - dates and policy maths
  - escalation rules
  - guards: abstention gate, no fake actions, no private digits
- Ponytail: 4 source modules, stdlib first, no frameworks. Each fix must be general behaviour, never question-specific.
- Repo stays private until just before submission. Commits only as the user's noreply identity.

## Checklist history
*(The order of work is in "Handoff → Next actions" above; this is the running record.)*
- [x] Refill missing 3.1 rows: all complete.
- [x] Report: every number taken from the CSVs; 3.5 vs 3.1 comparison included.
- [x] Voice: a Hindi caller stays in Hindi when reading out digits (`State.lang`). Verified live on PC021 turn 2.
- [ ] After the quota reset (12:30 IST): rerun PC021 by voice to confirm turns 3–4 in Hindi, then add it to `sample_outputs/`:
  1. copy `test_audio/PC021` to `sample_outputs/inputs/`
  2. rerun `run.py` into `sample_outputs/replies`
  3. add a row to `sample_outputs/README.md`
- [ ] Optional quality fix: a post-check that every "must state" computed fact (refund timing, RRN) appears in the reply.
- [x] `sample_outputs/` (13 files, no `.env` or dataset inside).
- [x] report.pdf (3 pages).
- [ ] Record the demo.mp4 (≤2 min, user): one question answered from the docs plus a follow-up, and one handover or "I don't know". Use `python app.py`.
- [x] Fresh-clone check (25 Oct, `%USERPROFILE%\vofresh`), following the README exactly:
  - install OK and `pip check` clean
  - **44/44 tests** pass without `PYTHONUTF8`
  - `run.py` on `sample_outputs/inputs` processed 13/13 files: Gnani STT transcripts, 13 reply WAVs, the silence fallback, and the batch never stopped
  - Two README fixes came out of it: clone into a **short path** on Windows (torch exceeds the 260-char path limit), and use `python -m pip` (Smart App Control blocked the new venv's `pip.exe`)
- [x] Clean-clone LLM step verified at 12:48 IST: 13/13 files, live calls, 0 errors. `%USERPROFILE%\vofresh` deleted, keys included.
- [x] Create the private GitHub repo and push (25 Oct). This also lets Claude Code cloud sessions run on the $100 credit.
- [ ] At submission: make the repo public, then build the submission zip.
- [ ] Ask the organizers (Discord):
  - whose LLM key runs the test (a free tier is ~500 calls/day; a 200-file run needs ~400)
  - how multi-turn audio is delivered
  - output schema
  - retrieval metric
  - exact deadline time

## How to resume
```bash
# venv lives outside OneDrive
"$USERPROFILE/.venvs/voiceops/Scripts/python.exe" -m pytest tests          # set PYTHONUTF8=1 on Windows
"$USERPROFILE/.venvs/voiceops/Scripts/python.exe" eval/evaluate.py --mode full            # retrieval|baseline|rag|full|conversations [--asr] [--rewrite]
"$USERPROFILE/.venvs/voiceops/Scripts/python.exe" run.py --input test_audio --output outputs/voice_test
"$USERPROFILE/.venvs/voiceops/Scripts/python.exe" eval/make_audio.py --out test_audio --questions PQ0003 --conversations PC002
"$USERPROFILE/.venvs/voiceops/Scripts/python.exe" app.py                    # Gradio demo at http://127.0.0.1:7860
```

## Where things live
- **`.env`** (git-ignored): `GNANI_API_KEY`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY` (Gemini), `LLM_MODEL`, `LLM_MIN_SECONDS`, `DATASET_DIR`.
  - Both keys were pasted in chat: **rotate them after submission**.
- **Dataset:** extracted into the repo root (git-ignored). Original zip: `C:\Users\shres\Downloads\Capstone_Project_Dataset_FTTT_2026.zip`.
- **Research notes with sources:** `docs/research/`
  - `course.md`: what the course taught
  - `gnani.md`: SDK 0.8.2 facts and gotchas
  - `stack.md`: LLM and retrieval options
  - `dataset.md`: traps and the date-rule proof
- **Full plan with rationale and the GPT-report comparison:** `C:\Users\shres\.claude\plans\c-users-shres-downloads-capstone-projec-mellow-volcano.md`
- **Git-ignored working output:** generated test audio in `test_audio/` and voice-run output in `outputs/`.

## Prompt to start a new chat
Paste this as the first message of a new Claude Code chat opened in the repo folder:

```text
I'm continuing my VoiceOps 2026 capstone (ZentroMart voice support agent, IIT-G C&A × Gnani.ai).
Repo: C:\Users\shres\OneDrive\Documents\claude\gnani (private GitHub: nightraven4545/voiceops-2026). Deadline: 26 Oct 2026.

1. Read PROJECT_STATE.md fully (start with "Handoff — start here"), then CLAUDE.md. Run `git log --oneline -8` and `git status`.
2. Check what's in flight (see the handoff) and the time vs the 12:30 IST Gemini quota reset.
3. Tell me in 5 short lines where things stand and what you'll do next, then do the first open item in "Next actions".

Rules:
- commit only as my noreply identity, never with AI co-author lines
- never print or commit keys from .env
- Gnani is the only STT/TTS
- ponytail (minimal code)
- every fix must be general, never question-specific
- after each milestone, update PROJECT_STATE.md and commit + push
- ask me before anything outward-facing or irreversible: making the repo public, deleting anything outside the repo except %USERPROFILE%\vofresh, spending money, messaging anyone
```

## Gotchas (each cost time once)
- **Gemini free quota** is per model and resets at **midnight Pacific = 12:30 IST**, not midnight IST.
  - On 429s, `eval/evaluate.py` stops after 3 failures in a row and keeps partial results.
  - LLM responses are cached in `.cache/llm/`, keyed by model + prompt, so re-runs only pay for changed prompts.
- **Windows Smart App Control** blocks brand-new binary wheels (pandas 3.1.0 DLL) → `pandas==3.0.3` is pinned. Use `PYTHONUTF8=1`.
- **Gnani SDK 0.8.2:**
  - The SDK rejects TTS `language="hi-en"` → Hinglish TTS goes through raw REST with `hi-en` (Poorvi).
  - REST STT takes one language and has no retries (our `_retry`). Keep clips ≤30 s.
  - Always pass the TTS `model`.
- **STT:**
  - `en-IN` writes spoken Hindi numbers as words.
  - `hi-IN` formatting writes "7,746 1,439" → `rules.numbers()` drops separators and joins digit groups.
  - A spoken SKU ("ELE zero zero one two") is not recoverable ("s q le 12").
- **Business days** count from the day *after* initiation (proved on all gold dates). Return windows are calendar days, deadline inclusive.
- **Retrieval:**
  - A raw follow-up ("and what if I'm not home?") must not outvote the rewrite (weights 1.0 / 0.5).
  - Down-weighting superseded sections was tried and **rejected**: it loses the pre-August electronics case.
