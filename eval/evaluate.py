"""Score the agent on the practice set.

  python eval/evaluate.py --mode retrieval [--asr]          # section-ID Recall@k / MRR, no LLM
  python eval/evaluate.py --mode baseline|rag|full [--asr]  # single questions (Step 1 / Step 2 / full agent)
  python eval/evaluate.py --mode conversations              # multi-turn practice conversations
Add --split dev|test to score only one fixed part (tune on dev, report test).
"""
import argparse
import csv
import hashlib
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import kb  # noqa: E402
from src.rules import DATASET, _MONTHS_EN, _MONTHS_HI, normalize_asr  # noqa: E402

RESULTS = ROOT / "eval" / "results" / os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")  # one folder per model
# Evidence the agent's code adds itself (greeting, verification, date maths, escalation),
# so retrieval is judged only on the content sections.
PROCESS_IDS = {"STY-1", "IDV-2", "IDV-3", "KB-00.1", "KB-00.3", "ESC-1"}
MONTHS = {m.lower(): i for i, m in enumerate(_MONTHS_EN, 1)} | {m: i for i, m in enumerate(_MONTHS_HI, 1)}
MONTHS |= {m[:3].lower(): i for i, m in enumerate(_MONTHS_EN, 1)} | {"फरवरी": 2, "सितम्बर": 9, "नवम्बर": 11, "दिसम्बर": 12}
_M = "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True))
DATE_RES = [re.compile(r"\b(2026)-(\d\d)-(\d\d)\b"),
            re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_M})\w*,?\s*(\d{{4}})?", re.I),
            re.compile(rf"\b({_M})\w*\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s*(\d{{4}})?", re.I)]


def practice(name):
    with open(DATASET / "practice" / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split(cell, sep=";"):
    return [x.strip() for x in cell.split(sep) if x.strip()]


def in_split(key, which):
    """Fixed 2/3 dev, 1/3 test by hash of the ID, so the split never changes between runs."""
    is_test = int(hashlib.md5(key.encode()).hexdigest(), 16) % 3 == 0
    return which == "all" or (which == "test") == is_test


def norm(text):
    """Case, Unicode form, Devanagari digits and the optional nukta (आख़िरी = आखिरी) don't change meaning."""
    text = unicodedata.normalize("NFKC", text).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return unicodedata.normalize("NFD", text).replace("़", "").casefold()


def dates_in(text):
    found = set()
    for m in DATE_RES[0].finditer(text):
        found.add(date(int(m[1]), int(m[2]), int(m[3])))
    for m in DATE_RES[1].finditer(text):
        found.add(_safe_date(m[3], MONTHS[m[2].lower()], m[1]))
    for m in DATE_RES[2].finditer(text):
        found.add(_safe_date(m[3], MONTHS[m[1].lower()], m[2]))
    return found - {None}


def _safe_date(year, month, day):
    try:
        return date(int(year or 2026), month, int(day))
    except ValueError:
        return None


def has_fact(reply, alternative):
    """One must_include alternative: a date (any format), a number (whole), or a phrase."""
    target = dates_in(alternative)
    if target:
        return bool(target & dates_in(norm(reply)))
    alt = norm(alternative)
    if re.fullmatch(r"\d+", alt):
        return re.search(rf"(?<!\d){alt}(?!\d)", norm(reply)) is not None
    return alt in norm(reply)


def score(reply, decision, ok_decisions, must, must_not, gold, sources):
    groups = [split(g, " / ") for g in split(must)]
    missing = [" / ".join(g) for g in groups if not any(has_fact(reply, a) for a in g)]
    violations = [p for p in split(must_not) if norm(p) in norm(reply)]
    gold = set(split(gold))
    row = {"decision_ok": decision in ok_decisions, "missing": " ; ".join(missing),
           "violations": " ; ".join(violations),
           "evidence_recall": round(len(gold & set(sources)) / len(gold), 2) if gold else ""}
    row["pass"] = row["decision_ok"] and not missing and not violations
    return row


def summarize(rows, by, title):
    groups = defaultdict(list)
    for r in rows:
        groups[r[by]].append(r)
        groups["all"].append(r)
    lines = [f"### {title}", "", f"| {by} | n | pass | decision | facts | no forbidden | evidence recall |",
             "|---|---|---|---|---|---|---|"]
    for key in sorted(groups, key=lambda k: (k == "all", k)):
        g = groups[key]
        ev = [r["evidence_recall"] for r in g if r["evidence_recall"] != ""]
        pct = lambda f: f"{100 * sum(map(f, g)) / len(g):.0f}%"  # noqa: E731
        lines.append(f"| {key} | {len(g)} | {pct(lambda r: r['pass'])} | {pct(lambda r: r['decision_ok'])} | "
                     f"{pct(lambda r: not r['missing'])} | {pct(lambda r: not r['violations'])} | "
                     f"{f'{sum(ev) / len(ev):.2f}' if ev else '-'} |")
    return "\n".join(lines)


def save(rows, name, table):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (RESULTS / f"{name}.md").write_text(table + "\n", encoding="utf-8")
    print(table, f"\n\nsaved {RESULTS.relative_to(ROOT)}/{name}.csv and .md")


def run_guarded(fn, rows, label):
    """Run fn per item; stop early (keeping results) if the LLM keeps failing, e.g. quota exhausted."""
    out, errors = [], 0
    for item in rows:
        try:
            out.append(fn(item))
            errors = 0
        except Exception as e:  # keep partial results; report why it stopped
            errors += 1
            print(f"  {label} {item.get('id') or item.get('conversation_id')}: {type(e).__name__}: {str(e)[:160]}")
            if errors >= 3:
                print("  3 errors in a row - stopping early (quota or connectivity).")
                break
    return out


def eval_questions(mode, asr, which):
    from src.agent import Agent

    def one(q):
        text = q["asr_text"] if asr else q["question"]
        r = Agent(mode).respond(text)
        s = score(r["reply"], r["decision"], split(q["acceptable_decisions"]) or [q["expected_decision"]],
                  q["must_include"], q["must_not_include"], q["gold_evidence"], r["sources"])
        print(f"  {q['id']} {'PASS' if s['pass'] else 'fail'} {r['decision']:8} {r['reply'][:90]}")
        return {"id": q["id"], "language": q["language"], "intent": q["intent"], **s, "decision": r["decision"],
                "expected": q["expected_decision"], "reply": r["reply"], "sources": " ; ".join(r["sources"]),
                "gold": q["gold_evidence"]}

    rows = run_guarded(one, [q for q in practice("questions.csv") if in_split(q["id"], which)], "question")
    name = f"questions_{mode}{'_asr' if asr else ''}_{which}"
    if rows:
        save(rows, name, summarize(rows, "language", f"{name} ({len(rows)} questions)"))


def eval_conversations(which):
    from src.agent import Agent
    convs = defaultdict(list)
    for t in practice("conversations.csv"):
        if in_split(t["conversation_id"], which):
            convs[t["conversation_id"]].append(t)

    def one(item):
        agent, rows = Agent("full"), []
        for t in sorted(item["turns"], key=lambda t: int(t["turn"])):
            r = agent.respond(t["customer_message"])
            s = score(r["reply"], r["decision"], [t["expected_decision"]], t["must_include"],
                      t["must_not_include"], t["gold_evidence"], r["sources"])
            want = {c.replace(" ", "") for c in split(t["expected_tool_calls"])}
            got = {c.replace(" ", "") for c in r["tool_calls"]}
            s["tools_ok"] = want == got
            s["pass"] = s["pass"] and s["tools_ok"]
            print(f"  {t['conversation_id']} t{t['turn']} {'PASS' if s['pass'] else 'fail'} {r['decision']:8} "
                  f"{r['reply'][:80]}")
            rows.append({"id": f"{t['conversation_id']}-t{t['turn']}", "scenario": t["scenario"],
                         "language": t["language"], **s, "decision": r["decision"], "expected": t["expected_decision"],
                         "tools": " ; ".join(r["tool_calls"]), "expected_tools": t["expected_tool_calls"],
                         "reply": r["reply"], "sources": " ; ".join(r["sources"]), "gold": t["gold_evidence"]})
        return rows

    done = run_guarded(one, [{"conversation_id": k, "turns": v} for k, v in sorted(convs.items())], "conversation")
    rows = [r for conv in done for r in conv]
    if rows:
        table = summarize(rows, "scenario", f"conversations_{which} ({len(rows)} turns)")
        tools = sum(r["tools_ok"] for r in rows) / len(rows)
        save(rows, f"conversations_{which}", table + f"\n\nTool calls exactly right: {100 * tools:.0f}% of turns")


def retrieval_scores(ranked, gold, ks=(1, 3, 5)):
    hits = [i for i, sid in enumerate(ranked) if sid in gold]
    row = {f"R@{k}": len(gold & set(ranked[:k])) / len(gold) for k in ks}
    row["MRR"] = 1 / (hits[0] + 1) if hits else 0.0
    return row


def eval_retrieval(asr, rewrite):
    """Raw customer text, or (--rewrite) the agent's own query pair: the LLM's English rewrite
    plus the raw text at half weight. Rewrites are read from the response cache only."""
    if rewrite:
        from src.agent import UNDERSTAND_SCHEMA, UNDERSTAND_SYSTEM, llm_json
    by_lang = defaultdict(list)
    misses, uncached = [], 0
    for q in practice("questions.csv"):
        gold = {g for g in split(q["gold_evidence"]) if not g.startswith("products.csv") and g not in PROCESS_IDS}
        if not gold:
            continue
        text = normalize_asr(q["asr_text"] if asr else q["question"])
        queries, weights = [text], [1.0]
        if rewrite:
            u = llm_json(UNDERSTAND_SYSTEM, f"CONVERSATION SO FAR:\n(none)\n\nLATEST MESSAGE:\n{text}",
                         UNDERSTAND_SCHEMA, cache_only=True)
            if u is None:
                uncached += 1
                continue
            queries, weights = [u["english_query"], text], [1.0, 0.5]
        ranked = [c["id"] for c in kb.retrieve(queries, k=6, weights=weights)]
        s = retrieval_scores(ranked, gold)
        by_lang[q["language"]].append(s)
        by_lang["all"].append(s)
        if s["R@5"] < 1:
            misses.append((q["id"], q["language"], sorted(gold), ranked[:5], text[:70]))
    print("| lang | n | R@1 | R@3 | R@5 | MRR |\n|---|---|---|---|---|---|")
    for lang, rows in by_lang.items():
        avg = {k: sum(r[k] for r in rows) / len(rows) for k in rows[0]}
        print(f"| {lang} | {len(rows)} | " + " | ".join(f"{avg[k]:.2f}" for k in ("R@1", "R@3", "R@5", "MRR")) + " |")
    if uncached:
        print(f"\n({uncached} questions skipped: rewrite not in cache)")
    print("\nMisses (gold not fully in top 5):")
    for m in misses:
        print(" ", *m)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["retrieval", "baseline", "rag", "full", "conversations"], required=True)
    ap.add_argument("--asr", action="store_true", help="use asr_text instead of the clean question")
    ap.add_argument("--split", choices=["all", "dev", "test"], default="all")
    ap.add_argument("--rewrite", action="store_true", help="retrieval: use the agent's cached English rewrite")
    args = ap.parse_args()
    if args.mode == "retrieval":
        eval_retrieval(args.asr, args.rewrite)
    elif args.mode == "conversations":
        eval_conversations(args.split)
    else:
        eval_questions(args.mode, args.asr, args.split)
