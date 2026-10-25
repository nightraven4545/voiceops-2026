# VoiceOps 2026 — ZentroMart voice support agent

**Author:** Shreshtha · **LLM:** Gemini `gemini-3.1-flash-lite` (free tier, OpenAI-compatible API) · **Speech:** Gnani `gnani-vachana` 0.8.2 (Prisma STT, Timbre v2.5 TTS) · **Code:** `run.py`, `src/` (4 modules), `eval/`, `tests/`

## 1. What we built, step by step

**Step 1: prompt only.** One LLM call. The system prompt sets the role (ZentroMart's AI support assistant), the limits (no promised refunds or actions; say when unsure) and the length. No documents.

**Step 2: grounded in the documents.**
- **Chunking:** each `## [SECTION-ID]` heading is one chunk: 84 chunks of 6–135 words, so a rule is never cut off from its heading.
- **Metadata:** every chunk keeps its `doc_type`, `status` and `effective_from`.
- **Retrieval:** BM25 (`bm25s`, with a romanized-Hindi stoplist) and multilingual embeddings (`intfloat/multilingual-e5-small`, numpy index), fused by reciprocal rank.
- **Query rewrite:** before retrieval, an LLM call rewrites the message into a standalone English query. The raw message also counts, at half weight.
- **Answering:** the model sees the top 6 sections sorted and labelled by authority (current policy > agent guide > help > FAQ > marketing; superseded sections marked). It must return the section IDs it used.

**Step 3: a real conversation.** Code, not the model, owns everything that must not go wrong.
- **Verification state machine.**
  - An order ID triggers `lookup_order(order_id)` and a request for the phone's last 4 digits or the delivery pincode.
  - The answer triggers the verified lookup. One retry, then refusal (IDV-3).
  - Phone, pincode and customer ID are stripped from tool results, so **private data never reaches the LLM**.
- **Policy maths in Python** (`src/rules.py`, unit-tested against the practice gold):
  - Business days count from the day *after* initiation, Mon–Sat, skipping the holiday table. This reproduces all 9 dated refund answers.
  - Return windows are calendar days, with the RET-3 exception (pre-August electronics: 10 days) and RET-8 (festive fashion: 30 days).
  - Refund arrival ranges per payment method, and the "more than 3 business days overdue" check.
  - The ₹49 pickup fee, refund timing after refusing at the door, and the refund reference number.
- **Policy-owned decisions.**
  - The ESC-1 triggers force an escalation: human requested, fraud, legal, safety, ≥2 earlier contacts, item > ₹10,000, or an overdue refund. The model cannot escalate on its own.
  - A compensation demand is refused unless it is the one case DEL-4 pays for (a late Express order).
- **Guards.**
  - A ticket is only mentioned after `create_ticket` returns `created=True`.
  - Replies claiming a cancellation, approval or credit, or showing private digits, are regenerated.
  - Evidence IDs that were not shown to the model are dropped.
  - **Abstention gate:** the model must mark whether the evidence actually answers the question. If not, code replaces the reply with "I don't have that information" plus an offer of a human colleague.

**Step 4: voice.**
- **Input:** `run.py` converts any audio format to 16 kHz mono, splits it into ≤30 s pieces and transcribes with Gnani `en-IN`.
- **Hindi second pass:** if the transcript looks Hindi (Hindi function words or Hindi number words), a second `hi-IN` pass runs and the agent receives both transcripts. `en-IN` writes spoken Hindi numbers as words ("saat hazaar…"); `hi-IN` returns digits.
- **Speech output:** replies are written for the ear (dates with month and year, order IDs in groups of four) and spoken with Kaveri (en-IN), Bhavna (hi-IN) or Poorvi (Hinglish, via the documented `hi-en` REST code, which the SDK rejects).
- **Robustness:** silence gets "Sorry, I didn't catch that". Sub-folders of audio are treated as one conversation. A failing file never stops the batch.

## 2. Evaluation

**How it is scored.** All numbers are on the dataset's practice files and come from `eval/evaluate.py`. A reply is **fully correct** only if all of these hold:
- the decision is one of the acceptable ones
- every `must_include` fact is present (dates matched by value across English and Hindi formats, numbers as whole numbers)
- no `must_not_include` phrase appears

Gold-evidence recall is reported separately. Result files are in `eval/results/<model>/`.

**Step 1 vs Step 2 vs full agent: 52 single questions (gemini-3.1-flash-lite)**

| | Step 1: prompt only | Step 2: + RAG | Full agent | Full agent, noisy `asr_text` |
|---|---|---|---|---|
| Fully correct | 15% | 83% | **96%** | **96%** |
| Required facts present | 23% | 87% | 98% | 98% |
| Acceptable decision | 75% | 90% | 98% | 98% |
| Forbidden phrase used | 0% | 0% | 0% | 0% |
| Gold-evidence recall | 0.00 | 0.72 | 0.83 | 0.85 |
| Fully correct: English / Hindi / Hinglish | 18 / 12 / 9% | 82 / 88 / 82% | 97 / 100 / 91% | 97 / 88 / 100% |

**What the jumps show.**
- **Step 1 → Step 2:** retrieval is worth 68 points. Without documents the model answers fluently and wrongly, for example the generic "5–7 days" for every refund.
- **Step 2 → full agent:** worth another 13 points, from:
  - catalog rows (warranty months, the Assured rule for marketplace sellers)
  - the date calculators
  - escalation decided by policy rules
  - the abstention gate
- **Noisy transcripts:** speech-recognition text (`asr_text`: spelled-out digits, misheard words) costs nothing overall, thanks to the transcript normaliser and the English rewrite.

**Retrieval** (section IDs, 46 answerable questions):

| Query used | R@1 | R@3 | R@5 | MRR | R@5 Hindi |
|---|---|---|---|---|---|
| Raw customer text | 0.30 | 0.48 | 0.68 | 0.50 | 0.43 |
| English rewrite + raw at half weight | 0.43 | 0.78 | **0.90** | 0.69 | **0.86** |
| Same, on noisy `asr_text` | 0.45 | 0.74 | 0.85 | 0.69 | — |

**Conversations: 23 conversations, 96 customer turns.**
- 93% of turns fully correct, **100% correct decisions, 100% exactly the expected tool calls** (`lookup_order` with and without the verification value, `create_ticket`), evidence recall 0.91.
- Per scenario:
  - **100%:** verification failure, high-value damage, human requested, repeat contact, return eligibility, topic switch, Express late credit, cancelling an unshipped order
  - **88%:** compensation demand
  - **75%:** refund status, where-is-my-order, cancelling a shipped order

**Voice end to end.** A 17-file test set, made with Gnani TTS plus a silent clip, ran through `run.py` with the batch never stopping: 8 questions in three languages, two 4-turn conversations (Hinglish high-value damage, Hindi failed verification) and silence.
- In the Hindi conversation, the caller's spoken code was read correctly: the `hi-IN` pass gives "1,266", which the extractor turns into `1266`. The agent then made the gold tool calls: verify, ask again, refuse.
- **Latency.** On the first live run a voice turn took 7–50 s on the free tier, much of it rate-limit waiting and retries. A rerun with the LLM answers cached, so speech only, took a median of 6.5 s (3–20 s): that is the Gnani STT + TTS share of a turn.

**Model comparison** (same code; `gemini-3.5-flash-lite` was used first):
- Fully correct: 21% (Step 1), 92% (full agent).
- Its Step 2 figure, 67%, was measured before the prompt fixes. Its conversation run was cut short by the daily quota.
- 3.1 was also faster in our probe: 2.3 s vs 5.2 s per call.

## 3. What went wrong, and what we fixed

| Problem the evaluation found | Fix |
|---|---|
| The section parser captured one section per file (`.*` under DOTALL swallowed the rest) | Anchored the heading pattern; a test asserts 84 sections |
| Dates in the query ("17 October 2026") pulled in sections that merely mention October | Stripping dates helped English but hurt festive-sale questions, where the date *is* the topic → reverted; the English rewrite solved it |
| The model invented answers to unanswerable questions ("GST invoice mil sakta hai") | `covered` flag + abstention gate |
| The model escalated on its own, and treated an Express-late question as compensation | Escalation comes only from the ESC-1 rules; a DEL-4 rule for compensation |
| Follow-ups ("and what if I'm not at home?"): the raw follow-up outvoted the context-aware rewrite | The raw query counts at half weight |
| Spoken Hindi numbers: `en-IN` gave "saat hazaar…", and Gnani's `hi-IN` formatting wrote "7,746 1,439" | Hindi number words trigger the `hi-IN` pass; the extractor drops thousands separators and joins split digit groups |
| A Hindi caller reading out digits was answered in Hinglish | The conversation keeps its language on such turns |
| The free LLM tier ran out mid-evaluation (~550 calls/day per model) | On-disk response cache; failed rows refilled on a later run |
| Tried down-weighting superseded sections in retrieval | Rejected: it dropped the gold `RETv3-2` for the pre-August electronics case the policy still covers |

**Still open, and what we would fix next.**
- **Facts left unstated.** In 3 conversation turns the decision was right but a computed fact was left out: the 7–10 day refund timing after refusing a parcel, or the refund reference number. Next step: a post-check that every fact tagged "must state" appears in the reply.
- **Too cautious on "what if I'm not at home?"** (2 turns). The abstention gate is conservative there. Next step: tune the rewrite toward the documents' wording ("delivery attempt").
- **Two single-question failures.** One unanswerable question (store pickup) still got an invented answer the gate didn't catch, and one asked an unnecessary "which colour?" before answering.
- **Correct but differently worded.** 2 failures use a Hindi synonym the strict string scorer doesn't list ("Mujhe khed hai" for "sorry", "क्वालिटी चेक" for "quality check"). A semantic scorer would pass them.
- **Spoken SKUs.** "ELE zero zero one two" comes back from STT as "s q le 12" and can't be recovered. Gnani's word-boosting (`bias_list`, REST only) is the next step.

## 4. Bonus work
- **Tests:** 45 automated tests, including scripted-LLM conversation tests (no API calls) for verification, ticket rules, abstention and language.
- **Evaluation tooling:** a Gnani-TTS test-audio generator; results stored per model; retrieval scored with and without the rewrite.
- **Live demo:** a Gradio app (`app.py`) showing each turn's decision, cited sections, tool calls and verification state.
