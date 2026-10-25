# LLM and retrieval stack for the VoiceOps 2026 capstone (ZentroMart agent): recommendation as of 24 Oct 2026

## 0. Bottom line

| Layer | Pick | Fallback / alternative |
|---|---|---|
| LLM for the batch the organizers run | **Claude Haiku 5.5** (`claude-haiku-5-5`), paid, about $0.2 per 200-file run | **Groq `openai/gpt-oss-120b`**, paid Developer plan, about $0.3 per run, fastest. **Sarvam `sarvam-105b`** if you can't pay in USD (₹100 free credit). |
| LLM for development and the LLM-as-judge | Gemini Flash-Lite free tier (~500 requests/day reported) or Groq free tier | — |
| Query handling for Hindi and Hinglish | An LLM rewrites each query to English (and pulls out the order ID) **before** retrieval | — |
| Dense embeddings | `BAAI/bge-m3` through sentence-transformers on CPU, stored in a numpy array | `intfloat/multilingual-e5-small` if the download size or speed hurts |
| Lexical search | `bm25s` with your own Hinglish stopword list and an English stemmer | `rank_bm25` (works, but unmaintained since 2022) |
| Combining dense and lexical | Reciprocal Rank Fusion (RRF, k=60), top 5–8 chunks | — |
| Reranker | **None at first.** Add `BAAI/bge-reranker-v2-m3` only if your own eval shows a section-ID recall gain worth 1–3 s of CPU time | — |
| Vector store | numpy (70×1024 float32 is about 287 KB) | FAISS or Chroma are unnecessary |
| Framework | Plain Python plus the provider SDK, pydantic for schemas | Not LangChain, LlamaIndex or DSPy |
| Eval | pytest plus your own scorers; date normalization in code, then an LLM judge | RAGAS or DeepEval only if you want their metric names in the report |
| Audio | `imageio-ffmpeg` (bundles ffmpeg) to convert everything to 16 kHz mono WAV; `sounddevice` + `soundfile` in a notebook; `gr.Audio` in Gradio | PyAV (`av`) |

## 1. What I checked on this laptop (read-only)

- Python 3.12.10. CPU is an i7-10750H (6 cores / 12 threads), 15.8 GB RAM.
- Already installed: `torch 2.13.0+cpu` (CUDA not available), `numpy 2.4.6`, `onnxruntime 1.29.0`, `anthropic 0.116.0` (old; current is 2.3.0).
- **ffmpeg is not on PATH.**
- `nvidia-smi` exists but failed without admin rights, so GPU status is UNVERIFIED. Assume CPU only.
- The project folder is under **OneDrive**. Keep the venv and the Hugging Face cache outside it, or OneDrive will sync and lock files. This is a recommendation, not a measured problem.

## (a) LLM options (prices per 1M tokens)

| Provider / model | Price in / out | Free tier (what limits a batch run) | Tools / JSON | temperature / seed |
|---|---|---|---|---|
| **Anthropic `claude-haiku-5-5`** | $0.10 / $0.50 (prompts ≤100K tokens). Batch API: $0.05 / $0.25 | No free tier. Start tier: 1,000 RPM, 2M input TPM, 400K output TPM. New orgs may start in a lower "Evaluation" tier. | Strict tool use (`strict: true`), structured outputs (`output_config.format`). Cached reads don't count toward the input rate limit. | **Can't be set.** Non-default sampling values return a 400 error, and API version 2026-10-21 removes `temperature`/`top_p`/`top_k` on all models. Thinking is on by default (effort default `medium`); set `output_config={"effort":"low"}` for lower latency. |
| Anthropic `claude-sonnet-5-5` | $2 / $10 | Same tiers | Same | Same |
| **Groq `openai/gpt-oss-120b`** | $0.15 / $0.60 (cached input $0.075). About 500 tokens/s. | Free tier: 30 RPM, **1K requests/day, 8K tokens/min, 200K tokens/day** | Tool use, JSON object mode, strict `json_schema`. Strict schemas **can't be combined with tools or streaming in the same call.** | `temperature` 0–2 and `seed` ("best effort to sample deterministically"). Reasoning effort low/medium/high. |
| Groq `openai/gpt-oss-20b` | $0.075 / $0.30, about 1,000 tokens/s | Same as 120b | Same | Same |
| Groq `qwen/qwen3.8-27b` (preview) | $0.80 / $4.00 | 30 RPM, 1K/day, 8K tokens/min | Strict schemas supported | `reasoning_effort` none/default |
| Groq Llama 3.x | Groq's model page now says "Contact sales (Enterprise)" | Not in the published limits table | — | — |
| **Sarvam `sarvam-105b`** | ₹15 / ₹60 (cached ₹5), plus GST | **₹100 free credit** for verified users; credits never expire. Starter plan: 40 RPM for 105b. | `tools`, `tool_choice` (none/auto/required/named), `response_format` json_schema | `temperature` 0–2 (default 0.2), "not bit-reproducible, even at 0". `seed` is beta, best effort. |
| Gemini `gemini-3.8-flash` (generally available since 2 Sep 2026) | $0.75 / $3.75 until 31 Dec 2026, then $1.50 / $7.50 | **About 20 requests/day free** (forum and aggregator reports; Google now shows limits only in AI Studio) | Function calling, `response_json_schema` | Google's migration checklist says to **remove temperature/top_p/top_k**; no `seed` guidance. Thinking levels low/medium/high (default medium; `minimal` returns an error). |
| Gemini `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` | $0.30 / $2.50 and $0.25 / $1.50 | **About 500 requests/day free** (aggregator, UNVERIFIED) | Same | The older Gemini 3 guide recommends keeping temperature at 1.0 |
| OpenAI `gpt-5-nano` / `gpt-5.4-nano` / `gpt-4.1-mini` / `gpt-4o-mini` | $0.05/$0.40, $0.20/$1.25, $0.40/$1.60, $0.15/$0.60 | No free tier | Tools and structured outputs | GPT-5 reasoning models don't accept temperature (UNVERIFIED for 5.4/5.6). `gpt-4.1-mini` accepts temperature and seed (best effort). |
| OpenRouter `:free` models | $0 | **20 RPM, 50 requests/day** (1,000/day once ≥10 credits have been purchased). The free list today has no gpt-oss, Llama, Qwen or Gemma, only niche models. | Varies | Varies |
| Cerebras | — | Trial only: $5 credit after adding a card, expires in 30 days, about 5 RPM and 1M tokens/day (aggregator, UNVERIFIED) | — | — |

**Batch math.** Assumption: 200 audio files × 2 LLM calls each (query rewrite + answer/tool loop) × about 4K input and 300 output tokens. That is about 400 calls, 1.6M input tokens and 0.12M output tokens.

| Option | Cost per run | Feasible in one sitting? |
|---|---|---|
| Haiku 5.5 | about $0.22 | Yes, 1,000 RPM |
| gpt-oss-120b, Groq paid | about $0.31 | Yes |
| gpt-oss-120b, Groq free | — | **No.** 8K tokens/min allows about 2 calls/min, and 200K tokens/day allows about 45 calls/day. |
| Sarvam-105b | about ₹31 + GST | Yes, so the free credit covers about 3 runs. 40 RPM means at least 10 minutes. |
| Gemini 3.8 Flash, free | — | **No** (about 20/day) |
| Gemini Flash-Lite, free | — | Borderline: one run, no retries |
| OpenRouter, free | — | **No** (50/day) |
| Gemini 3.1 Flash-Lite, paid | about $0.58 | Yes |
| Gemini 3.8 Flash, paid | about $1.65, plus thinking tokens | Yes |
| gpt-5-nano | about $0.13, plus reasoning tokens | Yes |

Reasoning and thinking tokens add to every figure above.

**Ranked recommendation**

1. **Primary: `claude-haiku-5-5`.**
   - Most rate-limit headroom per rupee, strict tools, and prompt caching for the system prompt and tool definitions.
   - Set a spend limit in the Console.
   - Hindi/Hinglish quality is UNVERIFIED. Confirm it with a 30–50 question bake-off on your own eval set; that comparison also counts toward the "own eval" points.
2. **Fallback: Groq `openai/gpt-oss-120b`.**
   - Free for development, paid Developer plan for the final run.
   - Lowest latency, which helps the voice UX score, and the only option here where `temperature=0` plus `seed` is accepted (best effort).
3. **If an international card is a problem: `sarvam-105b`.** INR billing, ₹100 free credit, built for Indian languages. Latency and reliability are UNVERIFIED.
4. **Development and judging only:** Gemini Flash-Lite free tier. Free-tier prompts are used to improve Google's products, which is fine for a fictional store.
5. **Avoid for the graded run:** any free tier (Gemini, Groq, OpenRouter, Cohere).

**Two ways to wire it**

- **Fewest lines:** one `openai` client and switch `base_url` between Groq (`https://api.groq.com/openai/v1`), Gemini (`https://generativelanguage.googleapis.com/v1beta/openai/`, still beta) and Sarvam (`https://api.sarvam.ai/v1`; OpenAI compatibility is not stated in Sarvam's docs, UNVERIFIED).
- **If Claude is primary:** use the official `anthropic` SDK, not an OpenAI shim, plus a small adapter for the fallback. Both SDKs retry on their own (`max_retries`, default 2; set it to 5), so you don't need `tenacity`.

```python
# Claude primary (anthropic>=2.x, API 2026-10-21: no temperature/top_p/top_k)
import anthropic
c = anthropic.Anthropic(max_retries=5)  # reads ANTHROPIC_API_KEY
TOOLS = [{"name": "lookup_order", "description": "...", "strict": True,
  "input_schema": {"type": "object", "additionalProperties": False,
    "required": ["order_id", "verification_value"],
    "properties": {"order_id": {"type": "string"}, "verification_value": {"type": "string"}}}},
  {"name": "create_ticket", "description": "...", "strict": True, "input_schema": {...}}]
r = c.messages.create(model="claude-haiku-5-5", max_tokens=1024,
      system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
      tools=TOOLS, output_config={"effort": "low"}, messages=history)
# loop while r.stop_reason == "tool_use"; append r.content (not just text);
# return all tool_result blocks in ONE user message; check for "refusal".

# Groq fallback via openai SDK
from openai import OpenAI
g = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"], max_retries=5)
r = g.chat.completions.create(model="openai/gpt-oss-120b", messages=msgs, tools=OAI_TOOLS,
      tool_choice="auto", temperature=0, seed=7, reasoning_effort="low")
```

**Reproducibility.** In Oct 2026 `temperature=0` with a seed is not a reliable lever:
- Claude rejects sampling parameters.
- Gemini 3.8 says to remove them.
- Sarvam says outputs are not bit-reproducible even at 0.
- Groq offers only "best effort".

Build determinism into the pipeline instead:
- Deterministic retrieval.
- Strict schemas for tool arguments and outputs.
- Format dates and amounts in code from tool results.
- A record/replay cache keyed on `sha256(model + messages + tools)` so eval re-runs are free and stable.
- Report the mean ± range over 3 runs.

## (b) Multilingual embeddings (corpus of about 70 chunks)

| Model | Size / dims / max length | Notes |
|---|---|---|
| **`BAAI/bge-m3`** | About 568M params (UNVERIFIED), 1024 dims, 8192 tokens, 100+ languages | No query prefix needed. Can also return sparse and ColBERT vectors through FlagEmbedding. Beat mE5 on Hindi-BEIR, which is Devanagari only. Download is about 2.2 GB (UNVERIFIED). |
| `intfloat/multilingual-e5-large-instruct` | 24 layers, 1024 dims, 512 tokens | Query format must be `"Instruct: {task}\nQuery: {q}"`; documents need no prefix. Led monolingual and cross-lingual recall in a study of 12 Indian languages (arXiv 2601.10205). |
| `intfloat/multilingual-e5-small` | 12 layers, 384 dims, 512 tokens | **The `"query: "` / `"passage: "` prefixes are mandatory.** Fastest option, lower quality. |
| `google/embeddinggemma-300m` | 300M params, 768 dims (can shrink to 512/256/128), 2048 tokens, 100+ languages | **Gated on Hugging Face** (you must accept the license), so the organizers' machine can't download it without an HF token. Doesn't support fp16. Has `encode_query` / `encode_document`. Avoid it for the submission. |
| `paraphrase-multilingual-MiniLM-L12-v2` | About 0.1B params, 384 dims, **128-token max** | Built for sentence similarity, and it truncates your chunks. Skip. |
| API: `gemini-embedding-2` | 128–3072 dims, 100+ languages, $0.20/M | Retrieval uses text prefixes (`task: search result \| query: …`). Adds a network call and rate limit to every query. |
| API: OpenAI `text-embedding-3-small` / `-large` | $0.02 / $0.13 per M | Hindi quality UNVERIFIED |
| API: Cohere | Trial: 2,000 inputs/min, but 1,000 calls/month | — |

**Speed on this CPU (estimates, not measured; models aren't installed).**
- bge-m3 index build: 70 chunks one time, roughly 15–40 s. Cache it with `np.save` and rebuild only when the docs' hash changes.
- bge-m3 query: roughly 0.1–0.3 s.
- e5-small: about 5× faster.

**Romanized Hinglish.** None of these models is shown to handle romanized Hindi well; Hindi-BEIR is Devanagari only. Two caveats:
- With `hi-IN`, Gnani STT may output English loanwords in Devanagari (for example "रिफंड"), which BM25 can't match against English docs. UNVERIFIED.
- The biggest lever is therefore an LLM step that turns the query into `{english_query, order_id, intent, reply_lang}`. Retrieve on the English query, plus the raw query on the dense side, and fuse the results.

```python
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("BAAI/bge-m3", device="cpu")
E = m.encode(chunks, normalize_embeddings=True, batch_size=8)  # (70,1024)
q = m.encode([q_en], normalize_embeddings=True)[0]
dense_rank = np.argsort(-(E @ q))
```

**Deployment risk.** The organizers' machine has to download the embedding model plus torch the first time it runs. Write the exact `pip install` and first-run download step into the README. If the download size is a problem, use e5-small.

## (c) Lexical search

- **`bm25s` 0.3.15 (22 Oct 2026):** numpy-only core, with a built-in tokenizer that takes your own stopwords and stemmer (`PyStemmer` 3.1.0 has Windows wheels for 3.12).
- **`rank_bm25` 0.2.2 (Feb 2022):** last release in 2022 (looks unmaintained), pure Python, does no preprocessing.
- At 70 chunks, speed doesn't matter. Pick `bm25s` because it's maintained and tokenizes for you.

**Tokenizing for Hinglish:**
- Apply NFKC normalization and lowercase, then `re.split(r"[^\w]+")` (Unicode-aware).
- Pull out order IDs with a regex **before** splitting.
- Remove English stopwords plus romanized Hindi function words: hai, ka, ki, ke, ko, mera, meri, mujhe, kya, kab, kaise, kitne, nahi, aur, se, mein, me, par, toh, ho, tha, raha, chahiye, kar, karna, do, de, plz.
- Map common Hinglish words to English: wapas→return, paisa wapas→refund, kharab/tuta→damaged/defective, badalna→exchange/replace.
- Stem with the English Snowball stemmer.
- Index each chunk with its doc title, section heading and the section-ID text, e.g. `RET-2`.

```python
import bm25s, Stemmer
st = Stemmer.Stemmer("english")
bm = bm25s.BM25()
bm.index(bm25s.tokenize(texts, stopwords=STOP, stemmer=st))
ids, sc = bm.retrieve(bm25s.tokenize([q_en], stopwords=STOP, stemmer=st), k=10)
# RRF: score[d] += 1/(60 + rank) across dense+bm25
```

## (d) Rerankers

| Reranker | Details | Verdict |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` | 0.6B params, Apache-2.0, multilingual | Use via `FlagReranker(...).compute_score([[q,p],...], normalize=True)` or `CrossEncoder(...).predict(pairs)` |
| `jinaai/jina-reranker-v2-base-multilingual` | 278M params | **License is CC-BY-NC-4.0** (research and evaluation only) and it needs `trust_remote_code=True` |
| Cohere rerank | Trial: 10 RPM and 1,000 calls/month | Unusable for the batch |

**Is it worth it at 70 chunks?** Not by default.
- Hybrid retrieval with RRF over 70 chunks is already strong.
- A 0.6B cross-encoder on 20 pairs costs roughly 1–3 s on this CPU (estimate), and that hurts voice latency.
- Better first step: have the answering LLM return `cited_section_ids` chosen from the top 8. That reranks for free inside a call you already make.
- Add the cross-encoder only if section-ID Recall@3 or MRR improves meaningfully on your eval.
- Open question for the organizers: is retrieval scored on recall@k or on precision? The answer decides whether you return the top-k IDs or only the cited ones.

## (e) Vector store

numpy is enough; this is confirmed by the arithmetic:
- 70 × 1024 float32 is about 287 KB.
- Cosine similarity is a dot product on normalized vectors (`E @ q`), which takes microseconds.
- FAISS or Chroma add dependencies and give nothing at this size.
- Save the vectors with `np.save` and the metadata (chunk_id, doc, section_id, text) in a JSON file.

## (f) Frameworks

- Use **plain Python** plus the provider SDK, and pydantic (already a dependency of the openai and anthropic SDKs) for tool and output schemas. That is about 300 lines: `retrieve.py`, `agent.py`, `tools.py`, `voice.py`, `run_batch.py`, `eval/`.
- LangChain and LlamaIndex add heavy abstractions that change often and make it hard to trace why a section ID was or wasn't retrieved.
- DSPy and Pydantic-AI are fine, but you don't need them for this project.
- The tool loop is a `while` loop over `stop_reason` / `tool_calls`.
- Option: expose retrieval as a `search_policy(query_en)` tool so the model writes the English query itself. Retrieval scoring needs it called on every turn; Haiku 5.5 isn't on Anthropic's list of models that dropped forced `tool_choice`, so forcing it should work (UNVERIFIED).

## (g) Evaluation tooling

**pytest 9.1.1 plus your own scorers:**
- Retrieval: Recall@k and MRR on section IDs.
- `must_include`: run each check in this order:
  1. Normalize: NFKC; Devanagari digits ०–९ → 0–9 via `str.translate`; a 12-entry month map that includes spelling variants (जनवरी, फ़रवरी/फरवरी, मार्च, अप्रैल, मई, जून, जुलाई, अगस्त, सितंबर/सितम्बर, अक्टूबर, नवंबर/नवम्बर, दिसंबर/दिसम्बर); and amounts (₹, Rs, rupaye → a number).
  2. Parse dates to `datetime.date` and compare them, so "27 अक्टूबर 2026", "27 October 2026" and "27/10/2026" all match.
  3. Only if that fails, ask an **LLM judge** for strict JSON `{"pass": bool, "reason": str}`, using a different model than the generator.
  4. Hand-check about 20 judge verdicts and report the agreement rate.
- Tool calls: correct name and argument match, ticket created only when it should be, verification enforced.
- Latency: p50 and p95 per stage.

**Other tools:**
- `dateparser` 1.4.3 has some Hindi support (per its changelog), but a dict is lighter.
- RAGAS 0.4.3 (Jan 2026) and DeepEval 4.3.1 (Oct 2026, has GEval and accepts a custom judge LLM) both need many LLM calls. Use them only if you want "faithfulness" numbers with a familiar name in the report.

## (h) Audio I/O

- **Gnani `gnani-vachana` 0.8.2** (22 Oct 2026, Python 3.9–3.13):
  - REST STT accepts **WAV, MP3, FLAC, OGG and M4A**, mono or stereo, resampled to 16 kHz automatically, **60 s maximum** per file.
  - Batch client: 100 files per job, 10 MB per file.
  - Language codes include `hi-IN`, `en-IN` and `auto`. The batch example passes `"hi-IN,en-IN"`; whether REST accepts that is UNVERIFIED.
  - TTS `timbre-v2.5`: 42 voices, `language` can be `auto`/`hi-IN`/`en-IN`/…, `speed` 0.85–1.15. A streaming client (`GnaniTTSStreamClient.synthesize_stream`) exists, which helps demo latency.
- **Conversion (the organizers may send any format).** Transcode **every** input to 16 kHz mono 16-bit WAV, and split into 55 s segments if a file is over 60 s. Doing it always is simpler than handling cases:
  - `imageio-ffmpeg` 0.6.0 bundles an ffmpeg binary in its Windows wheel, so the organizers' machine doesn't need a system ffmpeg.
    ```python
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", src, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", dst], check=True, capture_output=True)
    ```
  - Then get the duration with `soundfile.info(dst).duration` and slice with numpy if needed.
  - Alternative: PyAV 19.0.2 (bundles FFmpeg, Python ≥3.12).
  - Avoid `pydub` 0.25.1: last release Mar 2021, it needs ffmpeg anyway, and it depends on `audioop`, which is removed in Python 3.13.
- **Notebook demo:** `sounddevice` 0.5.6 + `soundfile` 0.14.0. Recording: `sd.rec(int(s*16000), samplerate=16000, channels=1, dtype="int16"); sd.wait(); sf.write("in.wav", rec, 16000, subtype="PCM_16")`. Playback: `IPython.display.Audio("reply.wav")`.
- **Gradio** 6.30.0 (Python ≥3.10):
  - Input: `gr.Audio(sources=["microphone","upload"], type="filepath", format="wav")`. Output: `gr.Audio(type="filepath", autoplay=True)`.
  - Gradio may need ffmpeg for transcoding (community reports; Gradio's docs don't say, UNVERIFIED). Install the full build with `winget install Gyan.FFmpeg`, which includes ffprobe, on the demo machine.
- **Streamlit:** `st.audio_input` is an option (version UNVERIFIED).

## Suggested pins (`requirements.txt`)

Pin what you actually tested with `pip freeze`. Several packages released in the last 1–3 days.

```
anthropic==2.3.0
openai==3.37.0
sentence-transformers==6.2.0
torch==2.13.0          # CPU build already installed
numpy==2.4.6
bm25s==0.3.15
PyStemmer==3.1.0
gnani-vachana==0.8.2
soundfile==0.14.0
sounddevice==0.5.6
imageio-ffmpeg==0.6.0
gradio==6.30.0
pytest==9.1.1
# optional: FlagEmbedding==1.4.2 (bge-m3 sparse vectors / reranker), google-genai==2.33.0, groq==1.7.0, av==19.0.2
```

## Open questions to settle with the organizers

1. When they run the batch, whose LLM key is used? Read keys from environment variables (`ANTHROPIC_API_KEY` / `GROQ_API_KEY`), never commit them, and set a spend cap.
2. What is the retrieval metric (recall@k or precision)?
3. Can a test audio file be longer than 60 s?
4. What are Gnani's rate limits during a 200-file run? Not published; UNVERIFIED.

## Sources

- Gemini: [models](https://ai.google.dev/gemini-api/docs/models), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [What's new in 3.8 Flash](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.8), [Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3), [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai), [embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [forum: 20 requests/day](https://discuss.ai.google.dev/t/gemini-3-8-flash-free-tier-20-rpd-is-too-limited-for-practical-evaluation/180609), [pricepertoken free limits](https://pricepertoken.com/endpoints/google-ai-studio/free)
- Groq: [rate limits](https://console.groq.com/docs/rate-limits), [models](https://console.groq.com/docs/models), [gpt-oss-120b](https://console.groq.com/docs/model/openai/gpt-oss-120b), [structured outputs](https://console.groq.com/docs/structured-outputs), [API reference](https://console.groq.com/docs/api-reference)
- Anthropic: [pricing](https://platform.claude.com/docs/en/about-claude/pricing), [rate limits](https://platform.claude.com/docs/en/api/rate-limits), [2026-10-21 API migration](https://platform.claude.com/docs/en/api/migration-2026-10-21)
- Sarvam: [pricing](https://docs.sarvam.ai/api/pricing.md), [chat completions](https://docs.sarvam.ai/api-reference-docs/chat/chat-completions), [rate limits](https://docs.sarvam.ai/api/ratelimits)
- OpenAI: [pricing](https://developers.openai.com/api/docs/pricing). OpenRouter: [limits](https://openrouter.ai/docs/api-reference/limits), [free models](https://openrouter.ai/models?max_price=0). Cohere: [rate limits](https://docs.cohere.com/docs/rate-limits). Cerebras: [BenchLM free tier](https://benchlm.ai/md/free-tier/cerebras.md)
- Models: [bge-m3](https://huggingface.co/BAAI/bge-m3), [multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct), [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small), [embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m), [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3), [jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual), [fastembed supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- Papers: [Hindi-BEIR](https://arxiv.org/pdf/2408.09437), [arXiv 2601.10205](https://arxiv.org/abs/2601.10205)
- PyPI: [bm25s](https://pypi.org/project/bm25s/), [rank-bm25](https://pypi.org/project/rank-bm25/), [gnani-vachana](https://pypi.org/project/gnani-vachana/), [gradio](https://pypi.org/project/gradio/), [soundfile](https://pypi.org/project/soundfile/), [sounddevice](https://pypi.org/project/sounddevice/), [imageio-ffmpeg](https://pypi.org/project/imageio-ffmpeg/) ([GitHub](https://github.com/imageio/imageio-ffmpeg)), [av](https://pypi.org/project/av/), [pydub](https://pypi.org/project/pydub/), [sentence-transformers](https://pypi.org/project/sentence-transformers/), [google-genai](https://pypi.org/project/google-genai/), [anthropic](https://pypi.org/project/anthropic/), [groq](https://pypi.org/project/groq/), [FlagEmbedding](https://pypi.org/project/FlagEmbedding/), [deepeval](https://pypi.org/project/deepeval/), [ragas](https://pypi.org/project/ragas/), [dateparser](https://pypi.org/project/dateparser/), [pytest](https://pypi.org/project/pytest/), [PyStemmer](https://pypi.org/project/PyStemmer/)
- Gradio: [Audio component docs](https://www.gradio.app/docs/gradio/audio)