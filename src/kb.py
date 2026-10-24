"""Knowledge base: one chunk per `## [SECTION-ID]` section, hybrid BM25 + dense retrieval."""
import functools
import hashlib
import re
from pathlib import Path

import numpy as np

from src.rules import DATASET

EMBED_MODEL = "intfloat/multilingual-e5-small"  # ponytail: swap to BAAI/bge-m3 only if dense recall is the bottleneck
CACHE = Path(__file__).resolve().parent.parent / ".cache"
LABEL = {"policy": "CURRENT POLICY", "agent_guide": "AGENT GUIDE", "help": "HELP ARTICLE",
         "faq": "FAQ (lower authority than policy)", "marketing": "MARKETING (never overrides policy)",
         "meta": "KB RULES"}
RANK = {"meta": 0, "policy": 1, "agent_guide": 2, "help": 3, "faq": 4, "marketing": 5}
# Romanized-Hindi function words, plus a few words customers use for policy terms
STOP = set("""a an the is are was were be to of and or in on at for with it this that i my me you your we
can do does will would should how what when where why which hai hain ka ki ke ko mera meri mere mujhe kya kab
kaise kitne kitna nahi nahin aur se mein me par pe toh to ho tha thi raha rahi chahiye kar karna karein do de
plz please hello hi haan uh so ji""".split())
SYNONYMS = {"wapas": "return", "vapas": "return", "lautana": "return", "kharab": "damaged", "tuta": "damaged",
            "toota": "damaged", "paisa": "refund", "paise": "refund", "badalna": "exchange"}


def _parse(path):
    raw = path.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^(\w+):\s*(.+)$", raw.split("---")[1], re.M))
    for sid, heading, body in re.findall(r"^## \[([^\]]+)\][ \t]*([^\n]*)\n(.*?)(?=^## \[|\Z)", raw, re.S | re.M):
        yield {"id": sid, "doc_id": meta["doc_id"], "doc_title": meta["title"], "doc_type": meta["doc_type"],
               "status": meta["status"], "effective_from": meta["effective_from"], "heading": heading.strip(),
               "text": body.strip()}


CHUNKS = [c for p in sorted((DATASET / "kb").glob("*.md")) for c in _parse(p)]
BY_ID = {c["id"]: c for c in CHUNKS}


def label(c):
    if c["status"] == "superseded":
        return "SUPERSEDED POLICY (applies only where the current policy says so, e.g. RET-3)"
    return LABEL[c["doc_type"]]


def _doc_text(c):
    return f"{c['doc_title']}. {c['heading']}. {c['text']}"


def _tokens(text):
    words = re.findall(r"\w+", text.lower())
    return [SYNONYMS.get(w, w) for w in words if w not in STOP]


@functools.cache
def _bm25():
    import bm25s
    import Stemmer
    stem = Stemmer.Stemmer("english").stemWord
    index = bm25s.BM25()
    index.index([[stem(t) for t in _tokens(_doc_text(c))] for c in CHUNKS], show_progress=False)
    return index, stem


@functools.cache
def _encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL, device="cpu")


@functools.cache
def _vectors():
    corpus = "\n".join(_doc_text(c) for c in CHUNKS)
    path = CACHE / f"kb_{hashlib.sha256((EMBED_MODEL + corpus).encode()).hexdigest()[:12]}.npy"
    if path.exists():
        return np.load(path)
    vecs = _encoder().encode([f"passage: {_doc_text(c)}" for c in CHUNKS], normalize_embeddings=True)
    CACHE.mkdir(exist_ok=True)
    np.save(path, vecs)
    return vecs


def _bm25_rank(query):
    index, stem = _bm25()
    toks = [stem(t) for t in _tokens(query)]
    if not toks:
        return []
    scores = index.get_scores(toks)
    return [i for i in np.argsort(-scores) if scores[i] > 0]


def _dense_rank(query):
    q = _encoder().encode(f"query: {query}", normalize_embeddings=True)
    return list(np.argsort(-(_vectors() @ q)))


def retrieve(queries, k=6, weights=None):
    """Reciprocal-rank fusion of BM25 and dense rankings over every query variant.

    Weights let a context-aware rewrite outvote a raw follow-up like "and what if I'm not home?".
    """
    fused = {}
    for q, w in zip(queries, weights or [1.0] * len(queries)):
        if not q:
            continue
        for ranking in (_bm25_rank(q), _dense_rank(q)):
            for rank, i in enumerate(ranking[:20]):
                fused[i] = fused.get(i, 0) + w / (60 + rank)
    top = sorted(fused, key=fused.get, reverse=True)[:k]
    return [{**CHUNKS[i], "score": round(fused[i], 4)} for i in top]
