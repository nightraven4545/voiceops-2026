"""Conversation logic with a scripted LLM: verification, tool calls, guards. No API calls."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import agent, kb  # noqa: E402


def fake_llm(compose):
    def llm_json(system, user, schema):
        if schema is agent.UNDERSTAND_SCHEMA:
            msg = user.split("LATEST MESSAGE:")[-1].lower()
            return {"english_query": "damaged item replacement" if "damage" in msg else
                    "where is my refund" if "refund" in msg else "order help",
                    "reply_lang": "hi-en", "intent": "damaged_item" if "damage" in msg else "order_help",
                    "products": ["Zentro Vista 43-inch 4K Smart TV"] if "tv" in msg else [], "payment_method": "none",
                    "refund_initiated_on": "", "delivered_on": "", "ordered_on": "",
                    "flags": ["damage_report"] if "damage" in msg else []}
        return {"covered": True, "decision": "answer", "reply": "Theek hai.", "evidence": ["DWM-3", "NOT-AN-ID"],
                "ticket_summary": "Verified caller reports a damaged TV worth over 10000 on this order.", **compose}
    return llm_json


@pytest.fixture
def scripted(monkeypatch):
    def use(**compose):
        monkeypatch.setattr(agent, "llm_json", fake_llm(compose))
        return agent.Agent()
    return use


def test_kb_has_every_section():
    assert len(kb.CHUNKS) == 84 and len(kb.BY_ID) == 84


def test_retrieval_finds_refund_timeline():
    assert "REF-2" in [c["id"] for c in kb.retrieve(["refund time for credit card after initiation"])]


def test_high_value_damage_conversation(scripted):  # practice PC002
    a = scripted()
    turns = [a.respond(m) for m in ["Hello, mujhe order ke baare mein help chahiye.", "Order number hai 8978 2837.",
                                    "Last four digits 4533 hain.",
                                    "Maine Zentro Vista 43-inch 4K Smart TV damage report kiya tha. Approve kar do na?"]]
    assert [t["decision"] for t in turns] == ["answer", "clarify", "answer", "escalate"]
    assert [t["tool_calls"] for t in turns] == [[], ["lookup_order(order_id=89782837)"],
                                                ["lookup_order(order_id=89782837, verification_value=4533)"],
                                                ["create_ticket()"]]
    assert turns[0]["sources"] == ["STY-1"] and "AI" in turns[0]["reply"]
    assert "ESC-1" in turns[3]["sources"] and "NOT-AN-ID" not in turns[3]["sources"]
    assert not {"delivery_pincode", "phone", "customer_id"} & set(a.state.order)
    a.respond("Kitna time lagega?")
    assert a.state.ticket_id and a.respond("Aur?")["tool_calls"] == []  # one ticket per conversation


def test_failed_verification_twice(scripted):  # practice PC021
    a = scripted()
    a.respond("नमस्ते")
    a.respond("ऑर्डर नंबर है 7746 1439।")
    first, second = a.respond("आख़िरी चार अंक 1266 हैं।"), a.respond("आख़िरी चार अंक 1266 हैं।")
    assert (first["decision"], second["decision"]) == ("clarify", "refuse")
    assert "IDV-3" in second["sources"] and a.state.order is None and a.state.locked


def test_switching_orders_keeps_the_lock(scripted):  # IDV-3: naming another order must not reset the retries
    a = scripted()
    for m in ["Order number hai 7746 1439.", "Last four digits 1266 hain.", "Last four digits 1266 hain."]:
        a.respond(m)
    a.respond("Order number hai 8978 2837.")
    assert a.respond("Last four digits 4533 hain.")["decision"] == "answer" and a.state.order  # other orders still verify
    back = a.respond("Order number hai 7746 1439.")
    assert back["decision"] == "refuse" and "IDV-3" in back["sources"] and a.state.order is None
    assert a.respond("Last four digits 1263 hain.")["tool_calls"] == []  # no third guess, even the right one


@pytest.mark.parametrize("order, proof, ask, needed", [
    ("1664 0894", "2108", "Mera refund kahan hai?", "315633825001"),  # practice PC010: RRN (REF-6)
    ("1591 1102", "440010", "Mujhe ise cancel karna hai.", "7")])     # practice PC019: refused at the door (CAN-2)
def test_post_check_adds_a_left_out_fact(monkeypatch, order, proof, ask, needed):
    composed = []

    def llm_json(system, user, schema):
        if schema is agent.UNDERSTAND_SCHEMA:
            msg = user.split("LATEST MESSAGE:")[-1].lower()
            return {"english_query": "where is my refund" if "refund" in msg else "order help", "reply_lang": "hi-en",
                    "intent": "order_help", "products": [], "payment_method": "none", "refund_initiated_on": "",
                    "delivered_on": "", "ordered_on": "", "flags": ["cancel_request"] if "cancel" in msg else []}
        composed.append(user)
        fixed = "LEFT OUT" in user
        return {"covered": True, "decision": "answer", "evidence": [], "ticket_summary": "",
                "reply": "Theek hai, RRN 315633825001, refund 7 se 10 din." if fixed else "Theek hai."}

    monkeypatch.setattr(agent, "llm_json", llm_json)
    monkeypatch.setattr(agent, "create_ticket", lambda *a, **k: {"created": True, "ticket_id": "T1"})
    a = agent.Agent()
    a.respond(f"Order number hai {order}."), a.respond(f"Last four digits {proof} hain.")
    assert sum("LEFT OUT" in u for u in composed) == 0  # nothing required yet: one compose call per turn
    assert needed in a.respond(ask)["reply"] and sum("LEFT OUT" in u for u in composed) == 1


def test_post_check_failure_keeps_first_reply_and_ticket(scripted, monkeypatch):
    llm = fake_llm({"reply": "Ticket raise kar raha hoon."})

    def flaky(system, user, schema):
        if "LEFT OUT" in user:
            raise RuntimeError("429")
        return llm(system, user, schema)

    monkeypatch.setattr(agent, "llm_json", flaky)
    monkeypatch.setattr(agent, "create_ticket", lambda *a, **k: {"created": True, "ticket_id": "T1"})
    a = agent.Agent()
    a.respond("Order number hai 1664 0894."), a.respond("Last four digits 2108 hain.")
    r = a.respond("Mera refund kahan hai?")  # overdue refund: escalate, and the RRN is a must-state fact
    assert (r["reply"], r["decision"], r["tool_calls"]) == ("Ticket raise kar raha hoon.", "escalate", ["create_ticket()"])


def test_hindi_voice_caller_keeps_hindi(scripted):
    a = scripted()
    a.state.lang = "hi"  # earlier turn was answered in Hindi
    r = a.respond("aakhiri chaar ank ek hazaar do sau chhiyasath hai", alt_text="आखिरी 4 अंक 1,266 हैं")
    assert r["lang"] == "hi"
    assert agent.Agent().respond("hello")["lang"] == "hi-en"  # text callers: model's choice stands


def test_abstains_when_evidence_does_not_cover(scripted):
    r = scripted(covered=False, reply="We do not offer that.").respond("Is there a student discount?")
    assert r["reply"].endswith(agent.NOT_COVERED["hi-en"]) and r["decision"] == "answer"


def test_never_claims_ticket_that_failed(scripted, monkeypatch):
    monkeypatch.setattr(agent, "create_ticket", lambda *a, **k: {"created": False, "error": "down"})
    a = scripted(ticket_summary="")
    for m in ["Order number hai 8978 2837.", "Last four digits 4533 hain.", "TV damage report kiya tha"]:
        r = a.respond(m)
    assert r["decision"] == "escalate" and "create_ticket()" not in r["tool_calls"] and "Sorry" in r["reply"]
