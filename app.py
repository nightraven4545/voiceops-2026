"""Live demo: speak to the agent (Gnani STT -> agent -> Gnani TTS) in the browser.

  python app.py      # then open http://127.0.0.1:7860
  Set LLM_FALLBACK_MODEL (e.g. gemini-3.5-flash-lite) to switch models at once if the main one is overloaded.
"""
import json
import os
import tempfile
import time
from datetime import date

os.environ.setdefault("LLM_MAX_RETRIES", "1")  # live: fail over in seconds instead of retrying for a minute

import gradio as gr  # noqa: E402

from run import NOT_HEARD, TROUBLE, mask, redact  # noqa: E402
from src import kb  # noqa: E402
from src.agent import Agent  # noqa: E402
from src.rules import ROOT  # noqa: E402
from src.voice import speak, transcribe  # noqa: E402

LOG = ROOT / "outputs" / "demo_log"


def turn(audio, typed, agent, chat):
    agent = agent or Agent()
    lang, t, heard, error = agent.state.lang or "en", {}, (typed or "").strip(), None
    t0 = time.time()
    try:
        heard, heard_hi = transcribe(audio) if audio else (heard, None)
        t["stt"] = round(time.time() - t0, 1)
        if not heard.strip() and not (heard_hi or "").strip():
            r = {"reply": NOT_HEARD[lang], "decision": "clarify", "lang": lang, "sources": [], "tool_calls": []}
        else:
            r = agent.respond(heard, alt_text=heard_hi)
            t["agent"] = r["seconds"]
    except Exception as e:  # an outage gets a spoken apology, never a page error; the call goes on
        error = type(e).__name__
        r = {"reply": TROUBLE[lang], "decision": "clarify", "lang": lang, "sources": [], "tool_calls": []}
    wav, t1 = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name, time.time()
    try:
        speak(r["reply"], r["lang"], wav)
        t["tts"] = round(time.time() - t1, 1)
    except Exception as e:
        wav, error = None, error or f"TTS {type(e).__name__}"
    chat = chat + [{"role": "user", "content": heard or "(nothing heard)"},
                   {"role": "assistant", "content": r["reply"]}]
    st = agent.state
    tools = mask(", ".join(r["tool_calls"]))
    details = (f"**Decision:** {r['decision']}  \n**Sources:** {', '.join(r['sources']) or '-'}  \n"
               f"**Tool calls:** {tools or '-'}  \n"
               f"**Order:** {st.order_id or '-'} · verified: {'yes' if st.order else 'no'} · "
               f"ticket: {st.ticket_id or '-'}  \n"
               f"**Seconds:** " + " · ".join(f"{k} {v}" for k, v in t.items()) + (f"  \n**Error:** {error}" if error else ""))
    rec = {"transcript": heard, "tool_calls": r["tool_calls"]}
    redact(rec)  # the log keeps no verification value, not even as the caller said it
    LOG.mkdir(parents=True, exist_ok=True)
    with open(LOG / f"{date.today()}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"heard": rec["transcript"], "reply": r["reply"], "decision": r["decision"], "sources": r["sources"],
                            "tool_calls": rec["tool_calls"], "seconds": t, "error": error}, ensure_ascii=False) + "\n")
    return chat, wav, details, agent, chat, None, ""


with gr.Blocks(title="ZentroMart voice support · Team Dstonks") as demo:
    gr.Markdown("## ZentroMart voice support · AI assistant\nAsk by voice (English, Hindi or Hinglish) or type. "
                "Answers come only from ZentroMart's policy documents and store data (catalog, pincode table, "
                "verified orders); the details below show the sources and tool calls.")
    agent_state, chat_state = gr.State(None), gr.State([])
    chatbot = gr.Chatbot(label="Conversation", height=380)
    with gr.Row():
        mic = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Your voice")
        reply_audio = gr.Audio(label="Agent reply", autoplay=True)
    typed = gr.Textbox(label="…or type", placeholder="e.g. How long does a refund to UPI take?")
    with gr.Row():
        send = gr.Button("Send", variant="primary")
        reset = gr.Button("New call")
    details = gr.Markdown()
    gr.Markdown("<sub>Team Dstonks (Shreshtha) · VoiceOps 2026 capstone, IIT Guwahati Consulting & Analytics Club × "
                "Gnani.ai · Speech: Gnani STT and TTS · Language model: Gemini</sub>")
    outputs = [chatbot, reply_audio, details, agent_state, chat_state, mic, typed]
    send.click(turn, [mic, typed, agent_state, chat_state], outputs)
    typed.submit(turn, [mic, typed, agent_state, chat_state], outputs)
    reset.click(lambda: ([], None, "", None, [], None, ""), None, outputs)

if __name__ == "__main__":
    kb.retrieve(["warm up"])  # load BM25 and the embedding model now, not on the first caller's turn
    demo.launch(theme=gr.themes.Soft())
