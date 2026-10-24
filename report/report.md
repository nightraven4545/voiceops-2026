# VoiceOps 2026 — ZentroMart voice support agent

**Team:** Shreshtha · **Repo:** github.com/nightraven4545/voiceops-2026 · **LLM:** Gemini `gemini-3.5-flash-lite` (free tier) · **Speech:** Gnani `gnani-vachana` 0.8.2 (Prisma STT, Timbre v2.5 TTS)

## 1. What we built, step by step

**Step 1 — prompt only.** One LLM call with a system prompt that sets the role (ZentroMart's AI support assistant), the limits (no promises of refunds or actions, say when unsure) and the reply length. No documents.

**Step 2 — grounded in the documents.** Each `## [SECTION-ID]` heading becomes one chunk (84 chunks, 6–135 words each, so no section is ever split from its heading). Every chunk keeps its `doc_type`, `status` and `effective_from`. Retrieval fuses BM25 (`bm25s`, with a romanized-Hindi stoplist) and multilingual dense embeddings (`intfloat/multilingual-e5-small`, numpy index) by reciprocal-rank fusion. Before retrieval, an LLM call rewrites the customer's message into a standalone English query. The answering call sees the top 6 sections sorted and labelled by authority (current policy > agent guide > help > FAQ > marketing; superseded marked as such) and must return the section IDs it relied on.

**Step 3 — a real conversation.** Code, not the model, owns the parts that must never go wrong:
- *Verification state machine.* An order ID triggers `lookup_order(order_id)` and a request for the phone's last 4 digits or the delivery pincode; the proof triggers the verified lookup; one retry, then refusal (IDV-3). Phone, pincode and customer ID are stripped from the tool result, so **unverified or private data never reaches the LLM**.
- *Deterministic policy maths* (`src/rules.py`, 37 unit tests built from the practice gold): business days counted from the day after initiation (Mon–Sat, minus the holiday table), return windows in calendar days with the RET-3 (pre-August electronics: 10 days) and RET-8 (festive fashion: 30 days) exceptions, refund arrival ranges per payment method, "more than 3 business days overdue", ₹49 pickup fee, refuse-at-door refund timing, refund reference numbers.
- *Policy-owned decisions.* ESC-1 triggers (human requested, fraud, legal, safety, ≥2 earlier contacts, item > ₹10,000, overdue refund) force an escalation; the model cannot escalate on its own. A compensation demand is refused unless it is the one case DEL-4 pays for (late Express).
- *Guards.* A ticket is mentioned only after `create_ticket` returns `created=True`; replies claiming a cancellation/approval/credit or showing private digits are regenerated; evidence IDs not shown to the model are dropped; **an abstention gate** replaces any answer the model marks as not covered by the evidence with "I don't have that information" + an offer of a human colleague.

**Step 4 — voice.** `run.py` converts any audio format to 16 kHz mono, splits it into ≤30 s pieces and transcribes with Gnani `en-IN`. When the transcript looks Hindi (function words or Hindi number words) a second `hi-IN` pass runs and both transcripts go to the agent, because `en-IN` writes spoken Hindi numbers as words ("saat hazaar…") while `hi-IN` returns digits. Replies are rewritten for the ear (dates with month and year, order IDs in groups of four) and spoken with Kaveri (en-IN), Bhavna (hi-IN) or Poorvi (Hinglish via the documented `hi-en` REST code, which the SDK rejects). Silence or an empty transcript gets "Sorry, I didn't catch that". Sub-folders are treated as conversations; a failing file never stops the batch.

## 2. Evaluation

All numbers are on the dataset's practice files, scored by `eval/evaluate.py`: decision ∈ acceptable decisions, every `must_include` fact present (dates matched by value across English/Hindi formats, numbers as whole numbers), no `must_not_include` phrase, and gold-evidence recall.

**Step 1 vs Step 2 vs full agent — 52 single questions**

| | Step 1: prompt only | Step 2: + RAG | Full agent |
|---|---|---|---|
| Fully correct | 21% | 67% | **92%** |
| Required facts present | 27% | 71% | 92% |
| Acceptable decision | 77% | 92% | 98% |
| Forbidden phrase used | 0% | 0% | 0% |
| Gold evidence recall | 0.00 | 0.63 | 0.84 |
| Fully correct — English / Hindi / Hinglish | 21 / 38 / 9% | 76 / 50 / 55% | 97 / 100 / 73% |

**Retrieval (section IDs, 46 answerable questions, no LLM in the loop except the cached rewrite)**

| Query used | R@1 | R@3 | R@5 | MRR | R@5 Hindi |
|---|---|---|---|---|---|
| Raw customer text | 0.30 | 0.48 | 0.68 | 0.50 | 0.43 |
| English rewrite + raw at half weight | 0.52 | 0.80 | **0.87** | **0.73** | 0.71 |

**Conversations — 23 conversations, 96 turns:** 83% of turns fully correct, 98% correct decision, **100% of turns made exactly the expected tool calls** (`lookup_order` with and without the verification value, `create_ticket`). *[Final rerun after the conversation fixes: TBD — free-tier quota ran out mid-run; partial rerun: 92% on 26 turns.]*

**Noisy transcripts (`asr_text`) and voice end to end:** *[TBD after quota reset.]* The 17-file Gnani test set (8 questions in three languages, two 4-turn conversations, silence) ran end to end; the run surfaced the Hindi-number and ITN issues below.

## 3. What went wrong, and what we fixed

| Problem found by the evaluation | Fix |
|---|---|
| Section parser captured one section per file (a `.*` under DOTALL swallowed the rest) | Anchored heading pattern; test asserts 84 sections |
| Dates in the query ("17 October 2026") pulled in sections that merely mention October dates | Tried stripping dates: helped English, hurt festive-sale questions where the date *is* the topic → reverted; the English rewrite solved it |
| Model invented answers to unanswerable questions ("GST invoice mil sakta hai", "we don't offer midnight delivery") | `covered` flag + abstention gate → all 5 unanswerables now abstain |
| Model escalated on its own; refused an Express-late question as "compensation" | Escalation decided only by ESC-1 rules in code; DEL-4 rule for compensation |
| Follow-ups ("and what if I'm not at home?") retrieved nothing useful — the raw follow-up outvoted the context-aware rewrite | Raw query at half weight in fusion |
| Spoken Hindi numbers: `en-IN` gave "saat hazaar saat sau…", and Gnani ITN wrote "7,746 1,439" | Hindi number words trigger the `hi-IN` pass; extractor drops thousands separators and joins split digit groups |
| Free LLM tier ran out (~550 calls/day) during evaluation | On-disk response cache; organizer run should use a key with headroom |
| Tried demoting superseded sections in retrieval | Rejected: it removed the gold `RETv3-2` for the pre-August electronics case that the policy still covers |

**What we would fix next:** spoken SKUs ("ELE zero zero one two" → "s q le 12") are not recoverable from STT text — Gnani's word-boosting (`bias_list`) on the REST API is the next step; Hindi answers still trail English on retrieval (R@5 0.71); a larger held-out set generated from the catalog and order tables would test generalisation beyond the 52 practice questions.

## 4. Bonus work
Automated regression suite (43 tests incl. a scripted-LLM conversation test), Gnani-TTS test-audio generator, three-language voice routing, Gradio live demo (`app.py`) showing decision, cited sections, tool calls and verification state.
