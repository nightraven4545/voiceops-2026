# Project state — VoiceOps 2026 capstone

> **Handoff file.** Read this first in any new chat. Update it (and commit) after every milestone and before ending a session.
> Last updated: **25 Oct 2026, 15:05 IST** · latest commit on `origin/main` (private GitHub repo).

## ▶ Handoff — start here
**Where things stand.** The agent is built, evaluated (full agent 96%, conversations 98%, tool calls 100% exact), documented, and pushed. The report PDF (4 pages: at the limit, add nothing) and `sample_outputs/` (17 files, PC021 included) are done. A clean clone installs and runs (64/64 tests). Both optional quality fixes are done; **stop changing the agent** and finish the submission. What's left is mostly finishing and submitting.

**In flight:** nothing. Only one chat should work from this file at a time (on 25 Oct two chats both picked up the same next action).
- The clean-clone check **passed** at 12:48 IST on 25 Oct: 13/13 files with **live** LLM calls (24 fresh responses, 0 errors), and PC002 made exactly the gold tool calls including `create_ticket()`.
  - 12/13 decisions matched the committed `sample_outputs`. **PQ0002** (spoken SKU garbled to "s q le 12") answered `clarify` ("which product or order ID?") instead of the committed `answer` ("I don't have that information" + human). Same transcript; the difference is Gemini sampling, because `src/` sets no `temperature`. Both replies are acceptable. Cached results are stable, but fresh runs (and the organizers' run) can differ turn by turn.
- Live latency on the free tier: median 20.9 s per voice turn (9–49 s).
- `%USERPROFILE%\vofresh`, including its `.env` copy of the keys, has been **deleted**.

**Next actions, in order (deadline 26 Oct 2026):**
1. ~~Clean-clone LLM check + delete `vofresh`~~: done (see above).
2. ~~PC021 by voice, add to `sample_outputs/`~~: done 13:16 IST (see Checklist history).
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
   - ~~a post-check that "must state" computed facts (refund timing, RRN) appear in the reply~~: done 25 Oct (see Checklist history)
   - ~~softer abstention on "what if I'm not home?" (PC011/PC012)~~: done 25 Oct as a "second look" (see Checklist history)
6. **Submission:**
   - make the repo public: `gh repo edit nightraven4545/voiceops-2026 --visibility public --accept-visibility-change-consequences`
   - build `Dstonks_voiceops.zip` (team name: **Dstonks**). The layout is the brief's p.14 "Submission ZIP structure": `README.md`, `.env.example`, `requirements.txt`, `run.py`, `src/`, `report.pdf`, `demo.mp4`, `sample_outputs/`; no `.env`, keys, venv or dataset copy. From the repo root, after committing everything (git archive takes only committed files; `--add-file` puts a file at the zip root):
     `git archive --format=zip -9 --add-file=report/report.pdf --add-file=demo.mp4 -o Dstonks_voiceops.zip HEAD README.md .env.example requirements.txt run.py src sample_outputs`
   - **Trial run 25 Oct 14:55** (without demo.mp4): 80 files, 10.4 MB. A scan with the real key values found neither key, no key patterns and no forbidden paths. Extracted to a fresh folder, the documented command answered PQ0003 end to end (live LLM, Gnani in and out, valid WAV) in 31 s.
   - The README now has the repository URL and a clone command (the brief requires the public GitHub URL).
   - still needed: `demo.mp4`, the repo made public
   - put the public repo URL in the submission
7. **After submission:** rotate the Gnani and Gemini keys; both were pasted in chat.

**Don't redo or undo:**
- the model choice (Gemini 3.1 free; the $100 is Claude Code cloud credit, not API)
- the per-model results folders
- the rejected superseded-section down-weighting
- the gold-aligned decisions: unanswerable → `answer`; compensation → `refuse`

**Budget:** ~500 Gemini calls/day per model, reset 12:30 IST. A full eval ≈ 450 calls. Cached answers are free. Used on 25 Oct after the reset: about 44 (clean clone 24, PC021 3, post-check 3, second look 10, samples 2, zip smoke test 2). The second look adds 1 call per abstaining turn (about 5% of turns), so a 200-file run needs ≈ 410.

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
| Rule + agent tests | 64 passing (`python -m pytest tests`) |
| Evaluation on `gemini-3.1-flash-lite` | **Complete**, every row filled |
| Voice end to end | 17/17 files processed, batch never stops. PC021 (Hindi, failed verification twice) verified live on 25 Oct: 4/4 turns pass the practice gold, replies in Devanagari, no private data in any Gemini prompt or reply. Reply WAVs now carry real header sizes |
| Report | `report/report.md` → `report/report.pdf` (4 pages, A4: the limit). Rebuild: `python report/build_pdf.py` (needs `pip install markdown`; uses headless Chrome, since Edge on this PC writes nothing) |
| Sample outputs | `sample_outputs/`: 17 files (8 questions, PC002 and PC021 conversations, silence), replayed from cached LLM answers with live calls blocked (`LLM_BASE_URL` pointed at a dead port); 0 errors |
| Git | **Private** repo https://github.com/nightraven4545/voiceops-2026 (`main`, pushed 25 Oct). Author `Shreshtha <77679539+nightraven4545@users.noreply.github.com>`, no AI trailers. Make it public only at submission: `gh repo edit nightraven4545/voiceops-2026 --visibility public --accept-visibility-change-consequences` |

## Results (practice set, `eval/results/<model>/`)
| Model | Step 1 baseline | Step 2 RAG | Full agent | Full, `asr_text` | Conversations (turns) | Tool calls |
|---|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` (**submission**) | 15% | 83% | **96%** | **96%** | **98%** (94/96 turns; dev 74/75, test 20/21), decisions 100% | 100% exact |
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
  - Hindi synonyms the strict scorer misses: PC009, PC016
- **Single questions:** PQ0053 invented an answer; PQ0058 asked "which colour?" unnecessarily.
- **Voice PC021 (scorer passes; noted, not fixed):**
  - turn 4 omits IDV-3's "offer general policy help" (the text-eval reply included it)
  - turn 2 greets again mid-conversation
  - the first turn of a call takes ~30 s (cold start of the embedding model and BM25)
- **Latent, not triggered by any practice case:**
  - the `FORBIDDEN` reply check retries once but has no final fallback if the retry still matches
  - `rules.numbers()` joins space-separated digit groups, so a bare "4 1266" would read as 41266

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
- [x] PC021 by voice, live, 25 Oct 13:01 IST (3 fresh Gemini calls, rest cached): `clarify, clarify, clarify, refuse`, the gold tool calls, 4/4 turns pass the repo's own conversation scorer. Three independent read-only checks (gold scorer, privacy, voice) confirmed it. Added to `sample_outputs/` (inputs, replies, README row).
- [x] **IDV-3 lock bypass fixed** (found by the privacy check): a new order ID used to reset `attempts`/`locked`, so alternating order IDs gave unlimited guesses at the last 4 digits. `State.failed` now counts failures per order for the whole conversation, and naming a locked order again gets `refuse`. A caller's other orders still verify. Test `test_switching_orders_keeps_the_lock`. The cached `conversations` and `full` evals replay byte-identical.
- [x] **Reply WAV header fixed**: Gnani streams `0xFFFFFFFF` RIFF/data sizes, so Python's `wave` read every reply as ~24.8 h. `speak()` now rewrites the file once with soundfile (same samples, PCM 16). All 17 sample replies regenerated; reply texts unchanged.
- [x] **Must-state post-check** (25 Oct). Code lists the facts a policy requires in this situation:
  - the RRN when a verified customer's turn is about a refund (REF-6)
  - `if_refused_at_door` when a shipped order's cancellation is refused (CAN-2; never on escalate, which must promise no time)

  If the reply lacks a fact's numbers (`rules.states`, whole numbers as the graders match them), one rewrite is asked for. It's kept only if it states the fact, keeps every number of the first reply and passes `FORBIDDEN`; if the call fails, the first reply stands. It's skipped when the abstention gate will replace the reply anyway.
  - **Cost:** a cache-only replay showed only PC010-t4, PC019-t4 and PC020-t4 (all dev) need a call; every other prompt is byte-identical. The live run used exactly 3 Gemini calls.
  - **Result:** conversations 89 → 92/96 (dev 69 → 72/75, test 20/21 unchanged). The full and full-ASR question evals replay byte-identical.
  - **Reviewed** before spending quota by 3 read-only reviewers (policy, code, voice). Fixes from the review: the guarded call, the keep-the-first-reply's-numbers rule, grader-exact number matching, skip-on-abstain, and a Devanagari "कैंसिल/रिफ़ंड … कर दिया" branch in `FORBIDDEN` (no cached reply matches it).
  - **Known limits:** COD's "nothing is charged" has no digits, so it's never enforced.
- [x] **Second look before abstaining** (25 Oct; the "softer abstention" item).
  - **Diagnosis:** PC011/PC012-t4 ("And what if I'm not at home?") were a retrieval miss, not over-caution. DEL-3 ("up to 3 delivery attempts") ranked 11th and 8th, outside the top 6, so `covered=false` was right. Loosening the gate would have shipped PC012's invented draft ("the courier will try again the next day").
  - **Fix (full mode only):** when the gate is about to abstain, compose once more with the top 12. The second reply is used only if it is `answer` + `covered`, cites a **new content section** (not `meta` or `agent_guide`, not one already shown) without citing every section, and passes `FORBIDDEN`. Otherwise, or on failure, it abstains as before. The must-state rewrite then builds on the wide prompt. Optional calls (`llm_json(optional=True)`) skip client retries, so a 429 falls back at once instead of after ~17 s.
  - **Cost and result:** a cache-only replay showed exactly 10 new calls across all three evals: the 2 targets plus the 8 correct abstentions (PQ0004/09/15/37 clean, PQ0009/15/37/53 ASR). Live: all 8 still abstain, and PC011/PC012-t4 now pass citing DEL-3. Conversations 92 → 94/96 (dev 72 → 74/75; test 20/21 unchanged, since no test turn could change). Question evals byte-identical.
  - **Reviewed** by 3 read-only reviewers before any quota was spent. From the review: answer-only acceptance, content-only "new" sections, the measure-against-shown fix, the cite-everything rejection, the wide prompt carried into the post-check, fail-fast optional calls, and 9 test rows. A mutation check showed every guard is pinned by a test.
  - **Samples:** PQ0002 and PQ0004 now take the second look (2 live calls). Both still abstain with identical text, so the committed `sample_outputs` were kept and their second-look answers are cached. The demo's "Is there a student discount?" still abstains (checked live; cached).
  - **Still failing:** PQ0053 (clean) and PQ0004 (ASR) invent an answer with `covered=true`, so they never reach the gate. An unrelated 7 and 10 in the reply count as stated. Facts with dates or ₹ amounts would need normalisation before being added to `must`.
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
- ask me before anything outward-facing or irreversible: making the repo public, deleting anything outside the repo, spending money, messaging anyone
```

## Gotchas (each cost time once)
- **Replays without spending quota:** set `LLM_BASE_URL=http://127.0.0.1:9/v1` in the shell (`.env` doesn't override it). Cache hits still work; a miss fails loudly instead of calling Gemini.
- **Timers:** a `sleep 60` wait loop fired 13 min late after the PC slept. Check result files, not timers.
- **Deleting a venv on Windows:** `Remove-Item` fails on torch's long paths. Git Bash `rm -rf` works but may need a second pass ("Permission denied" on the first).
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
