"""Live demo: speak to the agent (Gnani STT -> agent -> Gnani TTS) in the browser.

  python app.py      # then open http://127.0.0.1:7860
"""
import tempfile

import gradio as gr

from run import NOT_HEARD
from src.agent import Agent
from src.voice import speak, transcribe


def turn(audio, typed, agent, chat):
    agent = agent or Agent()
    heard, heard_hi = transcribe(audio) if audio else ((typed or "").strip(), None)
    if not heard.strip() and not (heard_hi or "").strip():
        r = {"reply": NOT_HEARD, "decision": "clarify", "lang": "en", "sources": [], "tool_calls": []}
    else:
        r = agent.respond(heard, alt_text=heard_hi)
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    speak(r["reply"], r["lang"], wav)
    chat = chat + [{"role": "user", "content": heard or "(nothing heard)"},
                   {"role": "assistant", "content": r["reply"]}]
    st = agent.state
    details = (f"**Decision:** {r['decision']}  \n**Sources:** {', '.join(r['sources']) or '-'}  \n"
               f"**Tool calls:** {', '.join(r['tool_calls']) or '-'}  \n"
               f"**Order:** {st.order_id or '-'} · verified: {'yes' if st.order else 'no'} · "
               f"ticket: {st.ticket_id or '-'}")
    return chat, wav, details, agent, chat, None, ""


with gr.Blocks(title="ZentroMart voice support") as demo:
    gr.Markdown("## ZentroMart support · AI assistant\nRecord a question (English, Hindi or Hinglish), "
                "or type one. Speech in and out is Gnani.")
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
    outputs = [chatbot, reply_audio, details, agent_state, chat_state, mic, typed]
    send.click(turn, [mic, typed, agent_state, chat_state], outputs)
    typed.submit(turn, [mic, typed, agent_state, chat_state], outputs)
    reset.click(lambda: ([], None, "", None, [], None, ""), None, outputs)

if __name__ == "__main__":
    demo.launch()
