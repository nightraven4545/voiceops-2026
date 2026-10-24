# VoiceOps 2026 capstone — working notes

Invariants (never break):
- Gnani is the only STT/TTS, even as a fallback (anything else disqualifies).
- No hardcoded answers; test answers come from the agent, never edited by hand.
- Dates, windows, refund timelines, verification retries and escalation thresholds live in `src/rules.py`, not in prompts.
- Unverified order data never reaches the LLM; strip phone/pincode/customer_id from tool results.
- Only say a ticket was created when `create_ticket` returned `created=True`. No cancel tool exists.
- Unanswerable questions use decision `answer` with "I don't have that information" + offer a human.
- Commits: author `Shreshtha <77679539+nightraven4545@users.noreply.github.com>`, no AI co-author trailers.

Commands (venv: `%USERPROFILE%\.venvs\voiceops`, set `PYTHONUTF8=1` on Windows):
- `python -m pytest tests`
- `python eval/evaluate.py --mode retrieval|baseline|rag|full|conversations [--asr] [--split dev|test]`
- `python run.py --input test_audio --output outputs`

Tune on `--split dev`; report `--split test`. Free Gemini tier: responses are cached in `.cache/llm`.
