"""Deterministic policy arithmetic and text normalisation.

Everything here is plain Python so dates, windows and escalation thresholds never
depend on the LLM. Numbers come from the KB sections cited next to each constant.
"""
import csv
import os
import re
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # first module every entry point imports, so keys and DATASET_DIR load once
DATASET = (ROOT / os.getenv("DATASET_DIR", "Capstone_Project_Dataset_FTTT_2026")).resolve()
TODAY = date(2026, 10, 20)  # KB-00.2

with open(DATASET / "data" / "holidays.csv", encoding="utf-8") as f:
    HOLIDAYS = {date.fromisoformat(r["date"]) for r in csv.DictReader(f)}  # KB-00.3

# REF-2: business days from initiation to arrival, (min, max). Wallet = instant.
REFUND_DAYS = {"upi": (1, 3), "card": (5, 7), "netbanking": (3, 5),
               "wallet": (0, 0), "cod_wallet": (0, 0), "cod_bank": (5, 7)}
# RET-2: calendar-day return windows; None = not returnable.
RETURN_DAYS = {"electronics": 7, "fashion": 15, "home_kitchen": 10, "beauty_sealed": 7,
               "books_media": 10, "grocery": None, "innerwear": None, "digital": None}
RET4_CUTOFF = date(2026, 8, 1)                          # RET-3: older electronics keep RETv3-2's 10 days
FESTIVE = (date(2026, 10, 1), date(2026, 10, 15))       # RET-8: fashion placed in sale -> 30 days
HIGH_VALUE = 10_000                                     # ESC-1.1 / DWM-3


def as_date(value):
    """'2026-10-17' or '2026-10-17T14:27' -> date; None stays None."""
    return date.fromisoformat(str(value)[:10]) if value else None


def is_business_day(d):
    return d.weekday() != 6 and d not in HOLIDAYS


def add_business_days(start, n):
    """Day 1 is the first business day after `start` (matches every gold date)."""
    d = as_date(start)
    while n > 0:
        d += timedelta(days=1)
        n -= is_business_day(d)
    return d


def refund_window(method, initiated):
    """(earliest, latest) arrival date for a refund initiated on `initiated` (REF-2)."""
    lo, hi = REFUND_DAYS[method]
    return add_business_days(initiated, lo), add_business_days(initiated, hi)


def refund_overdue(method, initiated, completed=None, today=TODAY):
    """ESC-1.5: not completed and more than 3 business days past the latest date."""
    return not completed and today > add_business_days(refund_window(method, initiated)[1], 3)


def return_days(category, delivered=None, placed=None):
    """Return window in calendar days (RET-2, RET-3, RET-8), or None if not returnable."""
    days = RETURN_DAYS.get(category)
    delivered, placed = as_date(delivered), as_date(placed)
    if category == "electronics" and delivered and delivered < RET4_CUTOFF:
        days = 10
    if category == "fashion" and placed and FESTIVE[0] <= placed <= FESTIVE[1]:
        days = 30
    return days


def return_deadline(category, delivered, placed=None):
    """Last calendar day to return an item, or None if the category is not returnable."""
    days = return_days(category, delivered, placed)
    return None if days is None else as_date(delivered) + timedelta(days=days)


def order_facts(order, today=TODAY):
    """Derived, policy-computed facts for a verified order (fed to the LLM as data)."""
    facts, flags = {}, []
    for item in order.get("items") or []:
        if order.get("delivered_on"):
            dl = return_deadline(item["return_category"], order["delivered_on"], order.get("placed_at"))
            facts[f"return_deadline[{item['sku']}]"] = (
                "not returnable" if dl is None else f"{dl} ({'open' if today <= dl else 'closed'})")
            if item["return_category"] == "fashion":  # RET-6
                facts[f"reverse_pickup_fee[{item['sku']}]"] = (
                    "none (Plus member)" if order.get("is_plus") else
                    "₹49 for a change-of-mind return; waived if damaged, defective or wrong")
    pay = order.get("payment_method")
    if pay == "cod":  # REF-3
        facts["refund_to_payment_method"] = ("COD: customer picks ZentroMart Wallet (instant, within 2 hours) or "
                                             "bank transfer (5 to 7 business days after bank details are verified)")
    elif pay in REFUND_DAYS:  # REF-2
        lo, hi = REFUND_DAYS[pay]
        facts["refund_to_payment_method"] = (f"{pay}: instant, within 2 hours of initiation" if hi == 0 else
                                             f"{pay}: {lo} to {hi} business days after initiation")
    if order.get("status") in ("shipped", "out_for_delivery", "delivery_attempted"):  # CAN-2, REF-1
        facts["if_refused_at_door"] = ("cash on delivery: nothing is charged" if pay == "cod" else
                                       "prepaid refund starts once the parcel is back at the warehouse, usually 7 to 10 "
                                       "calendar days after the last delivery attempt, then the payment-method timeline")
    for kind in ("return", "cancellation", "rto"):
        init, method = order.get(f"{kind}_refund_initiated_on"), order.get(f"{kind}_refund_method")
        if init and method in REFUND_DAYS:
            lo, hi = refund_window(method, init)
            facts[f"{kind}_refund_expected"] = f"{lo} to {hi}"
            if refund_overdue(method, init, order.get(f"{kind}_refund_completed_on"), today):
                flags.append(f"{kind}_refund_overdue")
        if order.get(f"{kind}_rrn"):  # REF-6
            facts[f"{kind}_refund_reference_number"] = (f"{order[f'{kind}_rrn']} (RRN: share it when the customer "
                                                        "says the money has not arrived)")
    if (order.get("contacts_last_7_days") or 0) >= 2:
        flags.append("repeat_contact")
    prices = {i["sku"]: i["unit_price_inr"] for i in order.get("items") or []}
    if order.get("damage_sku") and prices.get(order["damage_sku"], 0) > HIGH_VALUE:
        flags.append("high_value_damage")
    return facts, flags


# ---- ASR / text normalisation ------------------------------------------------
_DIGIT = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
          "six": "6", "seven": "7", "eight": "8", "nine": "9"}
_WEAK = {"to": "2", "too": "2", "for": "4"}  # misheard digits, only trusted inside a run
_MERGE = [(r"\bu p i\b", "upi"), (r"\bre fund", "refund"), (r"\bpin code\b", "pincode")]
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


_RUN = re.compile(r"\b(?:%s)(?:\s+(?:%s))+\b" % (("|".join([*_DIGIT, *_WEAK]),) * 2), re.I)


def _digits(m):
    words = m[0].lower().split()
    digits = "".join(_DIGIT.get(w) or _WEAK[w] for w in words)
    strong = sum(w in _DIGIT for w in words)
    weak = len(words) - strong
    # "five to seven days" must stay words; "zero zero to three" / "to zero to six" are IDs/years
    if not (strong >= 2 and (not weak or len(digits) >= 4)):
        return m[0]
    if len(digits) == 7:  # no ID here has 7 digits: an edge "to"/"for" is a word ("deliver to 411045")
        if words[0] in _WEAK:
            return f"{words[0]} {digits[1:]}"
        if words[-1] in _WEAK:
            return f"{digits[:-1]} {words[-1]}"
    return digits


def normalize_asr(text):
    """Spoken digits -> numerals ('ele-zero zero to three' -> 'ele-0023'), join split words."""
    text = (text or "").translate(_DEVANAGARI_DIGITS)
    text = re.sub(r"\b(double|triple) (\w+)", lambda m: " ".join([m[2]] * (2 if m[1].lower() == "double" else 3)), text, flags=re.I)
    for pat, rep in _MERGE:
        text = re.sub(pat, rep, text, flags=re.I)
    return _RUN.sub(_digits, text)


def numbers(text):
    """Whole numbers in a transcript. STT ITN writes '7,746 1,439' for a spoken order ID, so
    thousands separators go and digit groups split only by a space or hyphen are joined."""
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", (text or "").translate(_DEVANAGARI_DIGITS))
    return re.findall(r"\d+", re.sub(r"(?<=\d)[ -](?=\d)", "", text))


def states(reply, fact):
    """True when the reply contains every number in the fact as a whole number, as the graders check it."""
    reply = (reply or "").translate(_DEVANAGARI_DIGITS)
    return all(re.search(rf"(?<!\d){n}(?!\d)", reply) for n in re.findall(r"\d+", fact))


def find_order_id(text):
    return next((n for n in numbers(text) if len(n) == 8), None)


def find_proof(text):
    """Verification value the caller gave: 4-digit phone suffix or 6-digit pincode. The last such
    number wins, so the '4' in 'last 4 digits 1266' is ignored."""
    for n in reversed(numbers(text)):
        if len(n) in (4, 6):
            return n
        if len(n) == 10:
            return n[-4:]
    return None


def find_skus(text):
    return [f"{p.upper()}-{n}" for p, n in re.findall(r"\b(ELE|FSH|HOM|BTY|BKS|GRO|INR|DGT)[- ]?(\d{4})\b", text, re.I)]


_MONTHS_EN = "January February March April May June July August September October November December".split()
_MONTHS_HI = "जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर".split()


# Romanized Hindi function words: if a Latin-script transcript is full of these, the caller is speaking Hindi
HINDI_MARKERS = set("""hai hain kya mera meri mere mujhe aap aapka aapki nahi nahin kab kaise kitne kitna chahiye
karna kar raha rahi tha thi hoon hun ka ki ke ko se mein par bhi aur abhi wala wali""".split())


def sounds_hindi(text):
    words = re.findall(r"[a-z]+", text.lower())
    return bool(words) and sum(w in HINDI_MARKERS for w in words) / len(words) >= 0.15


def for_ear(text, lang="en"):
    """Reply text -> what TTS should read (STY-3): full dates with year, 8-digit IDs in 4+4."""
    months = _MONTHS_HI if lang == "hi" else _MONTHS_EN
    text = re.sub(r"\b(2026)-(\d\d)-(\d\d)\b", lambda m: f"{int(m[3])} {months[int(m[2]) - 1]} {m[1]}", text)
    text = re.sub(r"(?<!\d)(\d{4})(\d{4})(?!\d)", r"\1 \2", text)
    return re.sub(r"[*#`_]|^\s*[-•]\s*", "", text, flags=re.M).strip()
