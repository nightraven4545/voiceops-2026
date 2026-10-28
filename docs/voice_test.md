# Your own voice test

The judges will speak live, so test with real speech, not Gnani-generated audio.
**Record only your own voice.** The brief (p.12) forbids recording anyone else without written consent.

**Recording:**
- Use your phone or laptop mic, in any audio format `run.py` reads (wav, m4a, mp3, ogg…).
- Save into `recordings/`, which is git-ignored, so your voice never reaches GitHub.
- Single questions go directly in `recordings/`. Each conversation is a sub-folder with `turn1`, `turn2`, …
- Speak naturally: no pauses between digits unless that is how you talk.

| File | Say (any wording is fine) | Condition |
|---|---|---|
| `q01` | How long does a refund to UPI take? | quiet room |
| `q02` | (same as q01) | fan or TV on |
| `q03` | UPI pe refund kitne din mein aata hai? | Hinglish |
| `q04` | यूपीआई पर रिफ़ंड कितने दिन में आता है? | Hindi |
| `q05` | Do you offer EMI? | unsupported |
| `q06` | Kya aap gift wrap karte ho? | unsupported, Hinglish |
| `q07` | Can I pick up my order from your store? | unsupported |
| `q08` | Can I get Express delivery to pincode four one one zero four five? | digits, one by one |
| `q09` | Mera pincode do chaar aath zero zero ek hai, COD milega? | Hindi digit words |
| `q10` | My order is out for delivery but I won't be home, what happens? | fast speech |
| `q11` | I want to talk to a human. | handover |
| `q12` | Delivery late hui, mujhe compensation chahiye. | refuse |
| `q13` | Uh, my order… sorry, how many days do I get to return a shirt? | false start |
| `q14` | (3 s of silence, or a cough) | nothing said |
| `q15` | A ~25 s rambling Hinglish question about a refund | near Gnani's 30 s limit |
| `c1/turn1..4` | "Hi, I need help with my order" → "My order number is 8978 2837" → "The last four digits are 4533" → "My TV arrived damaged, please approve a replacement" | English, verification passes |
| `c2/turn1..4` | "नमस्ते, ऑर्डर के बारे में पूछना है" → "ऑर्डर नंबर 7746 1439" → "आखिरी चार अंक 1266" → (same again) | Hindi, verification fails twice |

## Run and score
1. Save the CSV below as `recordings/expected.csv`.
2. From the repo root, process the recordings:

```bash
python run.py --input recordings --output outputs/voice_real
```

3. Score the replies against the CSV:

```bash
python eval/evaluate.py --mode voice --run outputs/voice_real --questions recordings/expected.csv
```

The scorer reports, per clip:
- the decision
- the required phrases
- whether the digits you said were heard right
- median STT, agent and TTS seconds

```csv
id,language,question,intent,acceptable_decisions,expected_decision,must_include,must_not_include,gold_evidence,digits
q01,en,UPI refund time,refund_time,answer,answer,1 ; 3,,REF-2,
q02,en,UPI refund time (noise),refund_time,answer,answer,1 ; 3,,REF-2,
q03,hi-en,UPI refund time,refund_time,answer,answer,1 ; 3,,REF-2,
q04,hi,UPI refund time,refund_time,answer,answer,1 ; 3,,REF-2,
q05,en,EMI,unsupported,answer ; escalate,answer,don't have / do not have / no information / connect,,,
q06,hi-en,gift wrap,unsupported,answer ; escalate,answer,jaankari nahi / pata nahi / don't have / connect / सहयोगी,,,
q07,en,store pickup,unsupported,answer ; escalate,answer,don't have / do not have / no information / connect,,,
q08,en,express to 411045,pincode,answer,answer,Express,,DEL-5,411045
q09,hi-en,COD to 248001,pincode,answer,answer,,,DEL-5,248001
q10,en,not home for delivery,delivery,answer,answer,3,,DEL-3,
q11,en,talk to human,human,escalate,escalate,,,ESC-1,
q12,hi-en,late delivery compensation,compensation,refuse ; clarify,refuse,,,DEL-4,
q13,en,shirt return window,return_window,answer ; clarify,answer,,,,
q14,en,silence,silence,clarify,clarify,,,,
q15,hi-en,long refund question,refund,answer ; clarify ; escalate,answer,,,,
c1/turn1,en,greeting,order_help,clarify ; answer,clarify,AI,,,
c1/turn2,en,order id,verification,clarify,clarify,,,IDV-2,89782837
c1/turn3,en,phone suffix,verification,answer,answer,,,IDV-2,4533
c1/turn4,en,damaged TV,high_value_damage,escalate,escalate,,,ESC-1,
c2/turn1,hi,greeting,order_help,clarify ; answer,clarify,एआई,,,
c2/turn2,hi,order id,verification,clarify,clarify,,,IDV-2,77461439
c2/turn3,hi,wrong suffix,verification,clarify,clarify,,,IDV-3,1266
c2/turn4,hi,wrong suffix again,verification,refuse,refuse,,,IDV-3,1266
```

**The numbers that matter for a live demo:**
- digits heard right (order IDs and suffixes)
- unsupported questions that abstain instead of inventing a "no"
- median seconds per turn
