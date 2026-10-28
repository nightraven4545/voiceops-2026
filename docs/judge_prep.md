# Judge prep: explain the agent in 60 seconds

## One turn, end to end
1. **Hear:** Gnani STT, `en-IN` (`src/voice.py:67`).
   - If the words sound Hindi (`rules.sounds_hindi`) or contain Hindi number words, a second `hi-IN` pass runs, because `en-IN` writes Hindi digits as words.
   - Gnani is the only speech engine, even as a fallback.
2. **Normalise:** spoken digits ("eight nine seven eight…", "saat hazaar…") become numbers (`rules.normalize_asr`).
3. **Verify** (code only; `src/agent.py:267`).
   - An 8-digit order ID triggers `lookup_order(order_id)` and a request for the last 4 phone digits or the delivery pincode.
   - Two failures lock that order for the whole call (IDV-3), even if the caller switches orders.
   - Phone, pincode and customer ID are stripped before the LLM sees the order (`PRIVATE`, line 53).
4. **Understand:** LLM call 1 (line 310). It returns an English search query, reply language, products, dates and flags. Nothing else.
5. **Retrieve:** BM25 plus multilingual-e5, fused by reciprocal rank (`src/kb.py:96`). The query is the English rewrite (weight 1.0) plus the raw words (0.5).
6. **Compute in code:**
   - dates, refund windows, return deadlines (`src/rules.py`; "today" is fixed at 20 Oct 2026, as the brief says)
   - the catalog, the pincode table
   - the required decision (`_required`, line 509: escalate / refuse rules ESC-1, DEL-4, CAN-2)
7. **Compose:** LLM call 2 (line 363). It only phrases an answer from the evidence and computed facts, and says whether the evidence covers the question.
8. **Guards** (code):
   - no claimed actions or private digits (`FORBIDDEN`)
   - abstain if not covered, after one wider look (line 374)
   - a "we don't offer X" must be quoted from the documents (line 371)
   - must-state facts such as the RRN (line 390)
   - no claimed handover without a real ticket (line 402)
9. **Act:** `create_ticket` only when code decides to escalate; a ticket is mentioned only if `created=True` (line 425).
10. **Speak:** Gnani TTS: Kaveri (English), Bhavna (Hindi), Poorvi (Hinglish) (`src/voice.py:82`).

## Likely questions
- **Why RAG, why hybrid?**
  - On the 52 practice questions: prompt only 15%, adding RAG 83%, the full agent 96%.
  - BM25 catches exact terms (UPI, RRN, SKU). e5 catches paraphrase and Hindi.
  - Recall@5 is 0.68 on raw text and 0.90 with the English rewrite.
- **Old vs new policies?**
  - The authority order is current policy > agent guide > help > FAQ > marketing. A superseded section applies only where the current policy says so (e.g. items delivered before 1 Aug).
  - Down-weighting superseded sections was tried and rejected, because it broke that pre-August case.
- **Why are dates in code?**
  - LLMs miscount business days.
  - Business days count from the day after initiation (checked on every gold date), Mon–Sat minus holidays. Return windows are calendar days, deadline inclusive.
- **Can the LLM approve a refund or cancel?**
  - No. No such tool exists.
  - Decisions like escalate and refuse are made in code.
  - `FORBIDDEN` blocks "I have refunded / cancel kar diya", and the handover guard blocks "I'm connecting you" without a ticket.
- **Privacy?**
  - Order data is shown only after verification, with private fields stripped.
  - Verification values never go into ticket summaries, and are masked on the demo screen.
- **What fails?**
  - Hindi synonyms the strict scorer misses (PC009, PC016).
  - A spoken SKU is unrecoverable ("ELE zero zero one two" was heard as "s q le 12").
  - Asking for a phone number when the caller lost their order ID (demo turn 8).
  - On the free tier a turn takes ~21 s; the first turn's ~30 s cold start is now removed by warm-up.
- **Results** (Gemini 3.1 Flash-Lite, practice set):
  - full agent 96% (clean and ASR text)
  - conversations 94/96 turns
  - tool calls 100% exact

## Live-demo checklist
- Start with `LLM_FALLBACK_MODEL=gemini-3.5-flash-lite python app.py`. If 3.1 is overloaded, replies come from 3.5 within seconds.
- Ask one warm-up question, then press "New call".
- Good questions to show:
  - a UPI refund, plus the follow-up "and by card?"
  - an order flow with 8978 2837 and suffix 4533, then a TV damage report: ticket and handover
  - "Do you offer EMI?": "I don't have that information" + an offer to connect a human
- Each turn is logged (masked) in `outputs/demo_log/`.
