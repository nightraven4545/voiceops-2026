"""Conversation logic with a scripted LLM: verification, tool calls, guards. No API calls."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import agent, kb  # noqa: E402


def fake_llm(compose):
    def llm_json(system, user, schema, **_):
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

    def llm_json(system, user, schema, **_):
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

    def flaky(system, user, schema, **_):
        if "LEFT OUT" in user:
            raise RuntimeError("429")
        return llm(system, user, schema)

    monkeypatch.setattr(agent, "llm_json", flaky)
    monkeypatch.setattr(agent, "create_ticket", lambda *a, **k: {"created": True, "ticket_id": "T1"})
    a = agent.Agent()
    a.respond("Order number hai 1664 0894."), a.respond("Last four digits 2108 hain.")
    r = a.respond("Mera refund kahan hai?")  # overdue refund: escalate, and the RRN is a must-state fact
    assert (r["reply"], r["decision"], r["tool_calls"]) == ("Ticket raise kar raha hoon.", "escalate", ["create_ticket()"])


@pytest.mark.parametrize("mode, second, answered", [
    ("full", {}, True),                                   # the wider search found the answer
    ("full", {"evidence": ["TRK-2"]}, False),             # same sections judged again: a re-roll
    ("full", {"evidence": ["ESC-4"]}, False),             # a new agent-guide section answers nothing
    ("full", {"evidence": "all"}, False),                 # citing every section shows no grounding
    ("full", {"covered": False}, False),
    ("full", {"decision": "clarify"}, False),             # only a plain answer may replace an abstention
    ("full", {"reply": "I have refunded your money, call +91 98765 43210."}, False),  # FORBIDDEN
    ("full", "fail", False),                              # the extra call failed: abstain as before
    ("rag", {}, False)])                                  # Step 2 baseline keeps its single look
def test_second_look_before_abstaining(monkeypatch, mode, second, answered):  # practice PC011: DEL-3 ranked 11th
    ranked = [{**kb.BY_ID[i], "score": 0.0} for i in ("TRK-2", "RET-2", "CAN-3", "DEL-1", "IDV-3", "TRK-1",
                                                      "RVP-2", "ESC-4", "RETv3-2", "PAY-3", "DEL-3", "REF-3")]
    monkeypatch.setattr(kb, "retrieve", lambda queries, k=6, weights=None: ranked[:k])

    def llm_json(system, user, schema, **_):
        if schema is agent.UNDERSTAND_SCHEMA:
            return {"english_query": "delivery when customer is not at home", "reply_lang": "en", "intent": "delivery",
                    "products": [], "payment_method": "none", "refund_initiated_on": "", "delivered_on": "",
                    "ordered_on": "", "flags": []}
        if "[DEL-3]" not in user:
            return {"covered": False, "decision": "answer", "evidence": [], "ticket_summary": "", "reply": "Not sure."}
        if second == "fail":
            raise RuntimeError("429")
        out = {"covered": True, "decision": "answer", "evidence": ["DEL-3"], "ticket_summary": "",
               "reply": "The courier makes up to 3 attempts.", **second}
        return {**out, "evidence": re.findall(r"^\[([^\]]+)\]", user, re.M)} if out["evidence"] == "all" else out

    monkeypatch.setattr(agent, "llm_json", llm_json)
    r = agent.Agent(mode).respond("And what if I'm not at home?")
    assert r["reply"].endswith("up to 3 attempts.") is answered and ("DEL-3" in r["sources"]) is answered
    assert r["reply"].endswith(agent.NOT_COVERED["en"]) is not answered


@pytest.mark.parametrize("rows, says", [
    (["560034"], "metro city yes, delivery yes, cash on delivery enabled yes"),
    (["411045"], "Express no"),                    # a metro pincode without Express
    (["248001"], "cash on delivery enabled no"),
    (["194101"], "delivery no"),                   # listed but not served
    (["411045", "411014"], "Express varies by pincode, so ask which one")])  # Pune's two pincodes differ
def test_table_fact(rows, says):  # DEL-5, DEL-1
    assert says in agent.table_fact("x", [agent.PINCODES[p] for p in rows])


@pytest.mark.parametrize("say, alt, fact", [
    ("Can I get Express delivery to 411 045?", None, "pincode 411045 (Pune, Maharashtra): metro city yes, delivery yes"),
    ("can i get express delivery to four one one zero four five", None, "pincode 411045 (Pune"),   # spoken digits
    ("express pe delivery hogi kya", "४११०४५ पर एक्सप्रेस डिलीवरी होगी?", "pincode 411045 (Pune"),  # hi-IN fallback
    ("Do you deliver to pincode 999999?", None, "if the customer meant 999999 as a delivery pincode"),
    ("Do you deliver to Leh?", None, "Leh (1 pincode(s) in the table): metro city no, delivery no"),
    ("I paid 125000 for the TV, refund kab milega?", None, None),         # an amount is not a pincode
    ("Order number hai 1591 1102, pincode 440010.", None, None)])        # identity proof, not a delivery question
def test_pincode_and_city_facts(monkeypatch, say, alt, fact):
    prompts, llm = [], fake_llm({})
    monkeypatch.setattr(agent, "llm_json", lambda s, u, schema, **_: prompts.append(u) or llm(s, u, schema))
    r = agent.Agent().respond(say, alt_text=alt)
    if fact:
        assert fact in prompts[-1] and "DEL-5" in r["sources"]
    else:
        assert "pincode table" not in prompts[-1] and "pincode 440010 (" not in prompts[-1]


def test_verification_pincode_is_not_a_delivery_question(monkeypatch):
    prompts, llm = [], fake_llm({})
    monkeypatch.setattr(agent, "llm_json", lambda s, u, schema, **_: prompts.append(u) or llm(s, u, schema))
    a = agent.Agent()
    a.respond("Order number hai 1591 1102.")
    a.respond("Pincode 440010 hai.")  # PC019's proof
    assert "pincode 440010 (" not in prompts[-1] and a.state.order


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
