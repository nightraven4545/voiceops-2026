# Sample outputs

Produced with the submission command:

```bash
python run.py --input sample_outputs/inputs --output sample_outputs/replies
```

**Inputs** (`inputs/`): practice-set customer messages spoken with Gnani TTS, plus one silent clip.

| File | Customer says | Language | Tests |
|---|---|---|---|
| `PQ0002.wav` | SKU ELE-0012 pe ZentroMart Assured hai kya? Claim kaise karein? | Hinglish | catalog + warranty |
| `PQ0003.wav` | How fast are refunds to the ZentroMart Wallet? | English | FAQ vs policy conflict |
| `PQ0004.wav` | Can I schedule a delivery at midnight? | English | not in the documents → "I don't know" |
| `PQ0014.wav` | मुझे Pagecraft A5 Ruled Notebook (Pack of 4) लौटाने के लिए कितने दिन मिलेंगे? | Hindi | return window by category |
| `PQ0022.wav` | My refund to credit card was started on 17 October 2026. By which date…? | English | business-day date maths |
| `PQ0030.wav` | The Kestrel Book 14 Laptop (SKU ELE-0023) … has a crack. | English | high-value damage → ticket + handover |
| `PQ0048.wav` | मेरा सामान टूटा हुआ आया है, अब क्या करूँ? | Hindi | damaged item |
| `PQ0058.wav` | Mera order (Kestrel K7 Smartphone 256 GB) parso deliver hua… | Hinglish | relative date + electronics window |
| `silence.wav` | (nothing) | — | recovery: "Sorry, I didn't catch that" |
| `PC002/turn1-4.wav` | help → order ID → last 4 digits → "approve the TV replacement" | Hinglish | verification, then escalation with a ticket |
| `PC021/turn1-4.wav` | help → order ID → wrong last 4 digits → the same wrong digits again | Hindi | one retry, then refuse and share nothing (IDV-3); replies in Hindi although the profile says Marathi |

**Outputs** (`replies/`), one set per input file:
- `.wav`: the spoken reply
- `.txt`: the reply text
- `.json`: everything for that turn
  - both transcripts
  - reply language and decision
  - cited section IDs (`sources`)
  - the retrieved chunks with text and scores
  - tool calls
  - timing

`results.csv` summarises the whole run.

Notes:
- These replies were replayed from cached LLM answers with live LLM calls blocked; speech in and out is fresh Gnani STT/TTS.
  - The first 13 files reuse the evaluation run's answers.
  - PC021 reuses its live voice run of 25 Oct 2026, where all 4 turns passed the practice gold (decision, tool calls, required and forbidden phrases).
- Short delays here reflect the cache, not live LLM latency.
