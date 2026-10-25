# Project state — VoiceOps 2026 capstone

> **Handoff file.** Read this first in any new chat. Update it (and commit) after every milestone and before ending a session.
> Last updated: **25 Oct 2026, ~09:30 IST**.

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
| Report | `report/report.md` complete, ~2.5 pages, every number checked against the CSVs; needs PDF export |
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

## Next steps
- [x] Refill missing 3.1 rows: all complete.
- [x] Report: every number taken from the CSVs; 3.5 vs 3.1 comparison included.
- [x] Voice: a Hindi caller stays in Hindi when reading out digits (`State.lang`). Verified live on PC021 turn 2.
- [ ] After the quota reset (12:30 IST): rerun PC021 by voice to confirm turns 3–4 in Hindi.
- [ ] Optional quality fix: a post-check that every "must state" computed fact (refund timing, RRN) appears in the reply.
- [ ] `sample_outputs/` from a clean `run.py` run (no `.env`, no dataset copy).
- [ ] report.pdf (≤4 pp).
- [ ] Record the demo.mp4 (≤2 min, user): one question answered from the docs plus a follow-up, and one handover or "I don't know". Use `python app.py`.
- [ ] Fresh-clone check: follow the README exactly in a temp folder.
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
