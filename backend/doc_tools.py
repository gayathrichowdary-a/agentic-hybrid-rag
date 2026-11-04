"""
doc_tools.py  -  helpers for Compare Documents, Knowledge Graph and upload metadata.

Put this file next to main.py (in the backend folder).
It only needs scikit-learn, numpy and networkx, which you already have.
"""
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =====================================================================
#  SETTINGS YOU CAN CHANGE
# =====================================================================

# Reliability shown for each tier (percent). Edit these numbers freely.
TIER_RELIABILITY = {1: 96, 2: 85, 3: 65}

# Short names shown in the comparison table and the graph.
TIER_SHORT = {
    1: "Tier 1 (Authoritative)",
    2: "Tier 2 (Internal Verified)",
    3: "Tier 3 (Informal)",
}

# Full names shown in the Upload dropdown (must match page.js).
TIER_OPTIONS = [
    "Tier 1 (Authoritative / Regulatory Policy)",
    "Tier 2 (Internal Verified / Architecture & Runbooks)",
    "Tier 3 (Informal / Field Notes & Chat Archives)",
]

DEPARTMENTS = [
    "Legal & InfoSec",
    "DevOps & Infrastructure",
    "Software Engineering",
    "Human Resources",
    "Customer Operations",
]

EMBED_DIM = 384  # all-MiniLM-L6-v2 produces 384-number vectors
EMBED_MODEL = "all-MiniLM-L6-v2"

SHINGLE_WORDS = 5          # length of the word sequences used for "copied text"
CHUNK_WORDS = 120          # size of the pieces used to learn word importance
TOP_KEYWORDS = 12          # words shown in the keyword chart and word lists
GRAPH_OWN_KEYWORDS = 4     # most distinctive words shown for each document
GRAPH_CANDIDATES = 30      # a word counts as "shared" if it is in the top 30 of 2+ documents
GRAPH_MAX_SHARED = 14      # at most this many shared words are drawn
GRAPH_SIMILAR_MIN = 0.15   # documents this similar get a link in the graph...
GRAPH_SIMILAR_TOP = 2      # ...but each document links only to its closest matches
GRAPH_W, GRAPH_H = 900, 540  # drawing area; must match page.js (X = 50 + x*900, Y = 40 + y*540)

# =====================================================================
#  Tier helpers
# =====================================================================


def tier_number(tier_text):
    """'Tier 2 (Internal ...)' -> 2.  Returns None when no tier is set."""
    m = re.search(r"Tier\s*([123])", tier_text or "", re.I)
    return int(m.group(1)) if m else None


def tier_short(tier_text):
    n = tier_number(tier_text)
    return TIER_SHORT.get(n, "Not set")


def tier_reliability(tier_text):
    return TIER_RELIABILITY.get(tier_number(tier_text))  # None when not set


def clean_tier(value):
    """Accept the full dropdown text and return a valid option (default Tier 2)."""
    n = tier_number(value)
    return TIER_OPTIONS[(n or 2) - 1]


def clean_department(value):
    value = (value or "").strip()
    return value if value else DEPARTMENTS[0]


# =====================================================================
#  Metadata table (kept in your existing users.db)
# =====================================================================


def init_meta(get_connection):
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS doc_meta(
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            tier TEXT DEFAULT '',
            department TEXT DEFAULT '',
            words INTEGER DEFAULT 0,
            chunks INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT '',
            PRIMARY KEY (user_id, file_name)
        )
        """
    )
    conn.commit()
    conn.close()


def save_meta(get_connection, uid, name, tier, department, words, chunks):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO doc_meta (user_id, file_name, tier, department, words, chunks, uploaded_at)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(user_id, file_name) DO UPDATE SET
            tier=excluded.tier, department=excluded.department,
            words=excluded.words, chunks=excluded.chunks, uploaded_at=excluded.uploaded_at
        """,
        (uid, name, tier, department, words, chunks, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def update_tier_dept(get_connection, uid, name, tier, department):
    conn = get_connection()
    conn.execute(
        "UPDATE doc_meta SET tier=?, department=? WHERE user_id=? AND file_name=?",
        (tier, department, uid, name),
    )
    conn.commit()
    conn.close()


def read_meta(get_connection, uid):
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_name, tier, department, words, chunks, uploaded_at FROM doc_meta WHERE user_id=?",
        (uid,),
    ).fetchall()
    conn.close()
    return {
        r[0]: {"tier": r[1] or "", "department": r[2] or "", "words": r[3] or 0, "chunks": r[4] or 0, "uploaded_at": r[5] or ""}
        for r in rows
    }


def delete_meta(get_connection, uid):
    conn = get_connection()
    conn.execute("DELETE FROM doc_meta WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()


# =====================================================================
#  Reading document text
# =====================================================================


def pages_to_text(pages):
    """LangChain documents -> one string."""
    return "\n".join(getattr(p, "page_content", str(p)) for p in pages)


def count_words(text):
    return len(re.findall(r"[A-Za-z0-9]+", text or ""))


def save_text(vector_path, text):
    os.makedirs(vector_path, exist_ok=True)
    with open(os.path.join(vector_path, "fulltext.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def get_doc_text(uid, name):
    """Saved text of a document. For files uploaded before this feature, read the
    original upload once and save the text for next time."""
    vpath = os.path.join("vector_store", str(uid), name)
    cache = os.path.join(vpath, "fulltext.txt")
    if os.path.isfile(cache):
        with open(cache, encoding="utf-8") as f:
            return f.read()
    src = os.path.join("uploads", str(uid), name)
    if not os.path.isfile(src):
        return ""
    from loaders.loader_router import load_document  # imported late: it is heavy

    text = pages_to_text(load_document(src))
    if os.path.isdir(vpath):
        save_text(vpath, text)
    return text


def ensure_meta(get_connection, uid, name):
    """Fill in words/chunks for documents uploaded before tiers existed."""
    text = get_doc_text(uid, name)
    chunks = 0
    src = os.path.join("uploads", str(uid), name)
    if text and os.path.isfile(src):
        try:
            from loaders.loader_router import load_document
            from rag.chunker import chunk_text

            chunks = len(chunk_text(load_document(src)))
        except Exception:
            chunks = 0
    uploaded = ""
    idx = os.path.join("vector_store", str(uid), name, "index.faiss")
    if os.path.isfile(idx):
        uploaded = datetime.fromtimestamp(os.path.getmtime(idx), timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO doc_meta (user_id, file_name, tier, department, words, chunks, uploaded_at) VALUES (?,?,?,?,?,?,?)",
        (uid, name, "", "", count_words(text), chunks, uploaded),
    )
    conn.commit()
    conn.close()


def document_rows(get_connection, uid):
    """One dict per indexed document, with tier, reliability, words, etc."""
    base = os.path.join("vector_store", str(uid))
    names = []
    if os.path.isdir(base):
        names = [n for n in sorted(os.listdir(base)) if os.path.isfile(os.path.join(base, n, "index.faiss"))]
    meta = read_meta(get_connection, uid)
    rows = []
    for name in names:
        if name not in meta:
            try:
                ensure_meta(get_connection, uid, name)
                meta = read_meta(get_connection, uid)
            except Exception:
                pass
        m = meta.get(name, {"tier": "", "department": "", "words": 0, "chunks": 0, "uploaded_at": ""})
        rows.append(
            {
                "name": name,
                "tier": m["tier"],
                "tier_short": tier_short(m["tier"]),
                "reliability": tier_reliability(m["tier"]),
                "department": m["department"] or "Not set",
                "words": m["words"],
                "chunks": m["chunks"],
                "uploaded": (m["uploaded_at"] or "")[:10],
            }
        )
    return rows


def summary_stats(rows):
    rel = [r["reliability"] for r in rows if r["reliability"] is not None]
    return {
        "documents": len(rows),
        "chunks": sum(r["chunks"] for r in rows),
        "avg_reliability": round(sum(rel) / len(rel), 1) if rel else None,
        "embedding_dim": EMBED_DIM,
        "embedding_model": EMBED_MODEL,
    }


# =====================================================================
#  Comparing two documents
# =====================================================================


def _make_vectorizer():
    return TfidfVectorizer(
        stop_words="english",
        lowercase=True,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b",
    )


def _chunks(text, size=CHUNK_WORDS):
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] or [""]


def _shingles(text, n=SHINGLE_WORDS):
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < n:
        return set()
    return set(zip(*[words[i:] for i in range(n)]))


def similarity_label(topic, copied):
    if copied >= 0.5 or topic >= 0.85:
        return "Almost the same document", "🟣"
    if topic >= 0.55:
        return "Closely related", "🟢"
    if topic >= 0.30:
        return "Somewhat related", "🔵"
    if topic >= 0.10:
        return "Slightly related", "🟡"
    return "Not related", "🔴"


def compare_texts(text_a, text_b):
    """All numbers for the Compare Documents page."""
    empty = {
        "topic_similarity": 0.0,
        "vocabulary_overlap": 0.0,
        "copied_overlap": 0.0,
        "label": "Not related",
        "emoji": "🔴",
        "shared_keywords": [],
        "only_a": [],
        "only_b": [],
        "shared_count": 0,
        "note": "",
    }
    if not text_a.strip() or not text_b.strip():
        empty["note"] = "One of the documents has no readable text."
        return empty

    vec = _make_vectorizer()
    try:
        vec.fit(_chunks(text_a) + _chunks(text_b))
    except ValueError:  # no usable words at all
        empty["note"] = "The documents do not contain enough words to compare."
        return empty

    # 1) topic similarity: cosine of the two TF-IDF vectors
    matrix = vec.transform([text_a, text_b])
    topic = float(cosine_similarity(matrix[0], matrix[1])[0][0])

    # 2) vocabulary overlap: distinct words in both / distinct words in either
    analyze = vec.build_analyzer()
    count_a, count_b = Counter(analyze(text_a)), Counter(analyze(text_b))
    set_a, set_b = set(count_a), set(count_b)
    union = set_a | set_b
    vocab = len(set_a & set_b) / len(union) if union else 0.0

    # 3) copied text: identical 5-word sequences, measured against the shorter document
    sh_a, sh_b = _shingles(text_a), _shingles(text_b)
    smaller = min(len(sh_a), len(sh_b))
    copied = len(sh_a & sh_b) / smaller if smaller else 0.0

    idf = dict(zip(vec.get_feature_names_out(), vec.idf_))
    total_a, total_b = sum(count_a.values()) or 1, sum(count_b.values()) or 1

    shared = sorted(
        set_a & set_b,
        key=lambda w: math.sqrt((count_a[w] / total_a) * (count_b[w] / total_b)) * idf.get(w, 1.0),
        reverse=True,
    )[:TOP_KEYWORDS]
    only_a = sorted(set_a - set_b, key=lambda w: count_a[w] * idf.get(w, 1.0), reverse=True)[:TOP_KEYWORDS]
    only_b = sorted(set_b - set_a, key=lambda w: count_b[w] * idf.get(w, 1.0), reverse=True)[:TOP_KEYWORDS]

    label, emoji = similarity_label(topic, copied)
    return {
        "topic_similarity": round(topic, 4),
        "vocabulary_overlap": round(vocab, 4),
        "copied_overlap": round(copied, 4),
        "label": label,
        "emoji": emoji,
        "shared_keywords": [{"word": w, "a": count_a[w], "b": count_b[w]} for w in shared],
        "only_a": only_a,
        "only_b": only_b,
        "shared_count": len(set_a & set_b),
        "note": "",
    }


def excerpt(text, limit=6000):
    """Beginning, middle and end of a long document so the AI sees all of it."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    head, mid, tail = int(limit * 0.58), int(limit * 0.21), int(limit * 0.21)
    m = len(text) // 2
    return f"{text[:head]}\n[...]\n{text[m - mid // 2 : m + mid // 2]}\n[...]\n{text[-tail:]}"


def build_ai_prompt(row_a, row_b, text_a, text_b, numbers):
    def info(tag, r):
        return f"{tag}: {r['name']} | authority: {r['tier_short']} | department: {r['department']} | about {r['words']} words"

    return f"""You compare two documents for an enterprise knowledge base. Use ONLY the text given below. Never invent facts.

{info("Document A", row_a)}
{info("Document B", row_b)}

Measured similarity: topic {numbers['topic_similarity']*100:.1f}%, shared vocabulary {numbers['vocabulary_overlap']*100:.1f}%, copied text {numbers['copied_overlap']*100:.1f}%.

--- DOCUMENT A TEXT ---
{excerpt(text_a)}

--- DOCUMENT B TEXT ---
{excerpt(text_b)}

Reply in Markdown with exactly these four sections and nothing else:

## Summary of Document A
3 to 4 bullet points. Bold the key names or terms with **double asterisks**.

## Summary of Document B
3 to 4 bullet points. Bold the key names or terms with **double asterisks**.

## What they have in common
2 to 3 bullet points. If they share almost nothing, say so plainly.

## How they differ
2 to 4 bullet points. Mention which document comes from the more authoritative tier and what that means for trust.
"""


# =====================================================================
#  Knowledge graph
# =====================================================================


def _declutter(nodes, iterations=300):
    """Push nodes apart until no dot or label overlaps another (works in drawing pixels)."""
    import numpy as np

    n = len(nodes)
    if n < 2:
        return
    pos = np.array([[nd["x"] * GRAPH_W, nd["y"] * GRAPH_H] for nd in nodes], dtype=float)
    hw, hh, off = np.zeros(n), np.zeros(n), np.zeros(n)
    for i, nd in enumerate(nodes):
        kind = nd["type"]
        if kind == "keyword" and not nd.get("shared"):
            hw[i] = hh[i] = 8  # small dot, label only on hover
            continue
        r = {"document": 15, "tier": 11, "department": 11}.get(kind, 7)
        fs = 15 if kind == "document" else 12 if kind == "keyword" else 13
        text = nd["label"]
        limit = 26 if kind == "document" else 22
        width = min(len(text), limit) * fs * 0.56
        hw[i] = max(width / 2, r) + 6
        hh[i] = (2 * r + 20) / 2 + 4
        off[i] = (20) / 2  # label hangs below the dot
    for _ in range(iterations):
        cy = pos[:, 1] + off
        dx = pos[:, 0][:, None] - pos[:, 0][None, :]
        dy = cy[:, None] - cy[None, :]
        ox = (hw[:, None] + hw[None, :]) - np.abs(dx)
        oy = (hh[:, None] + hh[None, :]) - np.abs(dy)
        hit = (ox > 0) & (oy > 0)
        np.fill_diagonal(hit, False)
        if not hit.any():
            break
        move = np.zeros_like(pos)
        idx = np.arange(n)
        sx = np.where(dx == 0, np.sign(idx[:, None] - idx[None, :]), np.sign(dx))
        sy = np.where(dy == 0, np.sign(idx[:, None] - idx[None, :]), np.sign(dy))
        vertical = hit & (oy <= ox)
        horizontal = hit & (oy > ox)
        move[:, 1] += (vertical * (oy / 2 + 0.5) * sy).sum(axis=1)
        move[:, 0] += (horizontal * (ox / 2 + 0.5) * sx).sum(axis=1)
        pos += 0.6 * move
        pos[:, 0] = np.clip(pos[:, 0], hw, GRAPH_W - hw)
        pos[:, 1] = np.clip(pos[:, 1], 6, GRAPH_H - 24)
    for nd, (x, y) in zip(nodes, pos):
        nd["x"], nd["y"] = round(float(x) / GRAPH_W, 4), round(float(y) / GRAPH_H, 4)


def build_graph(docs):
    """
    docs: list of {"name", "text", "tier", "department"}
    Returns nodes, edges and positions (x, y between 0 and 1) for the page to draw.
    Documents link to their keywords, department and tier; similar documents link to each other.
    """
    docs = [d for d in docs if d["text"].strip()]
    if not docs:
        return {"nodes": [], "edges": [], "stats": {"documents": 0, "keywords": 0, "links": 0}}

    vec = _make_vectorizer()
    pieces = [c for d in docs for c in _chunks(d["text"])]
    try:
        vec.fit(pieces)
        matrix = vec.transform([d["text"] for d in docs])
        terms = vec.get_feature_names_out()
    except ValueError:
        matrix, terms = None, []

    # --- choose keywords: a few distinctive words per document + words several documents share
    cand = []
    if matrix is not None:
        for i in range(len(docs)):
            row = matrix[i].toarray().ravel()
            order = row.argsort()[::-1][:GRAPH_CANDIDATES]
            cand.append({terms[j]: float(row[j]) for j in order if row[j] > 0})
    else:
        cand = [{} for _ in docs]
    seen_in = Counter(w for c in cand for w in c)
    # words in every document say nothing about how documents differ, so skip them when there are 4+ documents
    pool = sorted(
        (w for w, k in seen_in.items() if k >= 2 and not (len(docs) >= 4 and k == len(docs))),
        key=lambda w: sum(c.get(w, 0) for c in cand),
        reverse=True,
    )[:GRAPH_MAX_SHARED]
    chosen = []
    for c in cand:
        own = sorted(c, key=c.get, reverse=True)[:GRAPH_OWN_KEYWORDS]
        keep = list(dict.fromkeys(own + [w for w in pool if w in c]))
        chosen.append([(w, c[w]) for w in keep])
    keyword_docs = Counter(w for ch in chosen for w, _ in ch)

    G = nx.Graph()
    meta = {}

    def add(node_id, label, kind, **extra):
        if node_id not in meta:
            meta[node_id] = {"id": node_id, "label": label, "type": kind, **extra}
            G.add_node(node_id)

    edges = []

    def link(a, b, kind, weight, **extra):
        edges.append({"source": a, "target": b, "type": kind, "weight": round(float(weight), 4), **extra})
        G.add_edge(a, b, weight=float(weight))

    for d, kws in zip(docs, chosen):
        did = f"doc:{d['name']}"
        n = tier_number(d["tier"])
        add(
            did, d["name"], "document",
            tier=tier_short(d["tier"]), department=d["department"] or "Not set",
            reliability=tier_reliability(d["tier"]),
        )
        add(f"tier:{n or 0}", TIER_SHORT.get(n, "Tier not set"), "tier")
        link(did, f"tier:{n or 0}", "has tier", 0.5)
        dept = d["department"] or "Not set"
        add(f"dept:{dept}", dept, "department")
        link(did, f"dept:{dept}", "belongs to", 0.5)
        for w, score in kws:
            add(f"kw:{w}", w, "keyword", shared=keyword_docs[w] > 1)
            link(did, f"kw:{w}", "mentions", 0.4 + score)

    if matrix is not None and len(docs) > 1:
        sims = cosine_similarity(matrix)
        pairs = set()
        for i in range(len(docs)):
            nearest = sorted((j for j in range(len(docs)) if j != i), key=lambda j: sims[i][j], reverse=True)
            for j in nearest[:GRAPH_SIMILAR_TOP]:
                if sims[i][j] >= GRAPH_SIMILAR_MIN:
                    pairs.add((min(i, j), max(i, j)))
        for i, j in sorted(pairs):
            link(f"doc:{docs[i]['name']}", f"doc:{docs[j]['name']}", "similar to", 0.4 + 1.5 * sims[i][j],
                 similarity=round(float(sims[i][j]), 3))

    n_nodes = G.number_of_nodes()
    pos = nx.spring_layout(G, k=2.4 / math.sqrt(max(n_nodes, 1)), seed=42, iterations=300, weight="weight")
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

    def norm(v, lo, hi):
        return 0.5 if hi - lo < 1e-9 else (v - lo) / (hi - lo)

    nodes = []
    for node_id, info in meta.items():
        x, y = pos[node_id]
        info["x"], info["y"] = norm(x, x0, x1), norm(y, y0, y1)
        info["degree"] = G.degree(node_id)
        nodes.append(info)
    _declutter(nodes)

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "documents": len(docs),
            "keywords": sum(1 for n in nodes if n["type"] == "keyword"),
            "links": len(edges),
        },
    }