import os
import sys

# ---- paths: code lives next to this file, user data lives in DATA_DIR ----
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [BASE] + [p for p in sys.path if p not in ("", ".")]
DATA = os.path.abspath(os.getenv("DATA_DIR", os.path.join(BASE, "data")))
for d in ("database", "uploads", "vector_store", "memory", "graph"):
    os.makedirs(os.path.join(DATA, d), exist_ok=True)
os.chdir(DATA)  # your modules use relative paths, so they now read/write inside DATA_DIR

import hashlib
import shutil
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

load_dotenv(os.path.join(BASE, ".env"))

import doc_tools  # NEW: compare, graph and tier/department helpers
from auth.auth_utils import hash_password, verify_password
from auth.database import create_database, get_connection
from agents.context_agent import ContextAgent
from agents.master_agent import MasterAgent
from agents.memory_agent import MemoryAgent
from agents.pdf_ranking_agent import rank_pdfs
from agents.profile_memory_agents import ProfileMemoryAgent
from database.chat_database import load_chat_history, save_chat
from database.memory_database import load_memory, save_memory
from database.profile_memory import load_profile_memory, save_profile_memory
from graph.graph_retriever import GraphRetriever
from langgraph_workflow.workflow import app as langgraph_app
from rag.retriever import get_context, retrieve_docs

create_database()
doc_tools.init_meta(get_connection)  # NEW: table that stores tier + department per document

SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".png", ".jpg", ".jpeg"}
MAX_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Agentic Hybrid RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")],
    allow_origin_regex=os.getenv("FRONTEND_ORIGIN_REGEX") or None,  # e.g. https://.*\.vercel\.app
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ auth
bearer = HTTPBearer()


def make_token(uid):
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": str(uid), "exp": exp}, SECRET, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        uid = int(jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Session expired. Please log in again.")
    conn = get_connection()
    row = conn.execute("SELECT id, full_name, username, email FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(401, "Account not found.")
    return {"id": row[0], "full_name": row[1], "username": row[2], "email": row[3]}


class SignupIn(BaseModel):
    full_name: str
    username: str
    email: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class ChatIn(BaseModel):
    query: str
    chat_name: str = "Chat 1"
    doc: str = "All Documents"


class CompareIn(BaseModel):  # NEW
    doc_a: str
    doc_b: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/signup")
def signup(body: SignupIn):
    if not all([body.full_name.strip(), body.username.strip(), body.email.strip(), body.password]):
        raise HTTPException(400, "Please fill all fields.")
    conn = get_connection()
    if conn.execute("SELECT id FROM users WHERE username=? OR email=?", (body.username, body.email)).fetchone():
        conn.close()
        raise HTTPException(409, "Username or email already exists.")
    conn.execute(
        "INSERT INTO users (full_name, username, email, password) VALUES (?,?,?,?)",
        (body.full_name, body.username, body.email, hash_password(body.password)),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/auth/login")
def login(body: LoginIn):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, full_name, username, email, password FROM users WHERE username=?", (body.username,)
    ).fetchone()
    conn.close()
    if not row or not verify_password(body.password, row[4]):
        raise HTTPException(401, "Wrong username or password.")
    user = {"id": row[0], "full_name": row[1], "username": row[2], "email": row[3]}
    return {"token": make_token(row[0]), "user": user}


@app.get("/me")
def me(user=Depends(current_user)):
    return user


# ------------------------------------------------------------- documents
_stores = {}  # (user_id, doc_name) -> FAISS index kept in memory after first load


def user_stores(uid):
    base = os.path.join("vector_store", str(uid))
    found = {}
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if not os.path.isfile(os.path.join(path, "index.faiss")):
                continue
            if (uid, name) not in _stores:
                from rag.embeddings import load_embedding
                from rag.vector_store import load_vector_db

                _stores[(uid, name)] = load_vector_db(path, load_embedding())
            found[name] = _stores[(uid, name)]
    return found


@app.get("/documents")
def list_documents(user=Depends(current_user)):
    base = os.path.join("vector_store", str(user["id"]))
    names = [n for n in sorted(os.listdir(base))] if os.path.isdir(base) else []
    return {"documents": [n for n in names if os.path.isfile(os.path.join(base, n, "index.faiss"))]}


@app.get("/documents/details")  # NEW: names + tier + reliability + words + chunks, plus totals
def document_details(user=Depends(current_user)):
    rows = doc_tools.document_rows(get_connection, user["id"])
    return {"documents": rows, "stats": doc_tools.summary_stats(rows)}


def _apply_tier(uid, name, tier, department):
    """Update tier/department of a document that is already indexed."""
    if name not in doc_tools.read_meta(get_connection, uid):
        doc_tools.ensure_meta(get_connection, uid, name)
    doc_tools.update_tier_dept(get_connection, uid, name, tier, department)


@app.post("/documents")
def upload_documents(
    files: list[UploadFile] = File(...),
    tier: str = Form(""),          # NEW: "Tier 1 (Authoritative / Regulatory Policy)" etc.
    department: str = Form(""),    # NEW: "Legal & InfoSec" etc.
    user=Depends(current_user),
):
    from loaders.loader_router import load_document
    from rag.chunker import chunk_text
    from rag.embeddings import load_embedding
    from rag.vector_store import create_vector_db

    uid = user["id"]
    tier = doc_tools.clean_tier(tier)
    department = doc_tools.clean_department(department)
    results = []
    for f in files:
        name = os.path.basename(f.filename or "")
        if os.path.splitext(name)[1].lower() not in ALLOWED_EXT:
            results.append({"name": name, "status": "Unsupported file type"})
            continue
        data = f.file.read()
        if len(data) > MAX_BYTES:
            results.append({"name": name, "status": "Larger than 10 MB"})
            continue

        up_dir = os.path.join("uploads", str(uid))
        os.makedirs(up_dir, exist_ok=True)
        file_path = os.path.join(up_dir, name)
        with open(file_path, "wb") as out:
            out.write(data)

        digest = hashlib.sha256(data).hexdigest()
        vpath = os.path.join("vector_store", str(uid), name)
        hash_file = os.path.join(vpath, "source_hash.txt")
        if os.path.exists(hash_file) and open(hash_file).read().strip() == digest:
            try:
                _apply_tier(uid, name, tier, department)
            except Exception as e:
                print("tier update skipped:", e)
            results.append({"name": name, "status": "Already indexed (tier and department updated)"})
            continue
        if os.path.exists(vpath):
            shutil.rmtree(vpath)
        try:
            pages = load_document(file_path)
            chunks = chunk_text(pages)
            if not chunks:
                results.append({"name": name, "status": "No readable text found"})
                continue
            text = doc_tools.pages_to_text(pages)
            db = create_vector_db(chunks, load_embedding())
            os.makedirs(vpath, exist_ok=True)
            db.save_local(vpath)
            with open(hash_file, "w") as hf:
                hf.write(digest)
            doc_tools.save_text(vpath, text)  # NEW: kept for Compare + Knowledge Graph
            doc_tools.save_meta(get_connection, uid, name, tier, department, doc_tools.count_words(text), len(chunks))
            _stores.pop((uid, name), None)
            results.append({"name": name, "status": "Indexed"})
        except Exception as e:
            results.append({"name": name, "status": f"Failed: {e}"})
    return {"results": results}


@app.delete("/documents")
def clear_documents(user=Depends(current_user)):
    uid = user["id"]
    for folder in ("uploads", "vector_store"):
        shutil.rmtree(os.path.join(folder, str(uid)), ignore_errors=True)
    for key in [k for k in _stores if k[0] == uid]:
        _stores.pop(key)
    doc_tools.delete_meta(get_connection, uid)
    return {"ok": True}


# ------------------------------------------------- compare + knowledge graph  (NEW)
def _pair(uid, a, b):
    if a == b:
        raise HTTPException(400, "Pick two different documents.")
    rows = {r["name"]: r for r in doc_tools.document_rows(get_connection, uid)}
    if a not in rows or b not in rows:
        raise HTTPException(404, "Document not found. Refresh the page and pick again.")
    return rows[a], rows[b]


@app.post("/compare")
def compare_documents(body: CompareIn, user=Depends(current_user)):
    uid = user["id"]
    ra, rb = _pair(uid, body.doc_a, body.doc_b)
    ta, tb = doc_tools.get_doc_text(uid, ra["name"]), doc_tools.get_doc_text(uid, rb["name"])
    ra["words"] = ra["words"] or doc_tools.count_words(ta)
    rb["words"] = rb["words"] or doc_tools.count_words(tb)
    return {"a": ra, "b": rb, **doc_tools.compare_texts(ta, tb)}


@app.post("/compare/ai")
def compare_documents_ai(body: CompareIn, user=Depends(current_user)):
    uid = user["id"]
    ra, rb = _pair(uid, body.doc_a, body.doc_b)
    ta, tb = doc_tools.get_doc_text(uid, ra["name"]), doc_tools.get_doc_text(uid, rb["name"])
    if not ta.strip() or not tb.strip():
        raise HTTPException(400, "One of the documents has no readable text to summarise.")
    ra["words"] = ra["words"] or doc_tools.count_words(ta)
    rb["words"] = rb["words"] or doc_tools.count_words(tb)
    numbers = doc_tools.compare_texts(ta, tb)
    prompt = doc_tools.build_ai_prompt(ra, rb, ta, tb, numbers)
    try:
        from llm.groq_llm import generate_answer

        summary = generate_answer(prompt)  # one argument = used as a ready-made prompt
    except Exception as e:
        raise HTTPException(502, f"AI comparison failed: {e}")
    return {"summary": summary}


@app.get("/graph")
def knowledge_graph(user=Depends(current_user)):
    uid = user["id"]
    rows = doc_tools.document_rows(get_connection, uid)
    docs = [
        {"name": r["name"], "text": doc_tools.get_doc_text(uid, r["name"]), "tier": r["tier"], "department": r["department"]}
        for r in rows
    ]
    return doc_tools.build_graph(docs)


# ------------------------------------------------------------------ chat
@app.get("/chats")
def get_chats(user=Depends(current_user)):
    return {"chats": load_chat_history(user["id"])}


@app.delete("/chats/{chat_name}")
def delete_chat(chat_name: str, user=Depends(current_user)):
    conn = get_connection()
    conn.execute("DELETE FROM chat_history WHERE user_id=? AND chat_name=?", (user["id"], chat_name))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/memory")
def get_memory(user=Depends(current_user)):
    return {"memories": load_memory(user["id"])}


@app.post("/chat")
def chat(body: ChatIn, user=Depends(current_user)):
    uid, query = user["id"], body.query.strip()
    if not query:
        raise HTTPException(400, "Type a question first.")
    stores = user_stores(uid)
    if not stores:
        raise HTTPException(400, "Upload a document first.")

    decision = MasterAgent().process(query).strip().lower()
    ranking = rank_pdfs(query, stores)  # [(name, distance)], lower distance = better match
    if not ranking:
        raise HTTPException(404, "No relevant document found.")

    best_doc, best_score = ranking[0]
    # distance on normalised embeddings: smaller is closer
    confidence = "High" if best_score < 0.9 else "Medium" if best_score < 1.3 else "Low"

    if body.doc != "All Documents" and body.doc in stores:
        picked = [body.doc]
    else:
        picked = [n for n, _ in ranking[:5]]
    all_docs = [(n, d) for n in picked for d in retrieve_docs(stores[n], query)]

    context = get_context(all_docs)
    graph_context = GraphRetriever().get_subgraph_context(query)
    history = load_chat_history(uid).get(body.chat_name, [])

    try:
        result = langgraph_app.invoke({
            "query": query,
            "user_id": uid,
            "vector_db": stores[picked[0]],
            "uploaded_documents": list(stores.keys()),
            "vector_context": context,
            "graph_context": graph_context,
            "system_context": str(load_profile_memory(uid)),
            "memory_context": ContextAgent().build_context(history),
            "web_context": "",
            "decision": "",
            "final_answer": "",
        })
    except Exception as e:
        raise HTTPException(502, f"Answer generation failed: {e}")
    answer = result["final_answer"]

    # long-term memory (best effort: never fail the chat because of it)
    try:
        for key, value in ProfileMemoryAgent().extract(query).items():
            save_profile_memory(uid, key, value)
        agent = MemoryAgent()
        convo = f"User:\n{query}\n\nAssistant:\n{answer}\n"
        if agent.should_store(convo):
            save_memory(uid, agent.extract_memory(convo))
    except Exception as e:
        print("memory step skipped:", e)

    sources = sorted({n for n, _ in all_docs})
    full_answer = answer + "\n\n---\nSources referenced:\n" + "\n".join(f"- {s}" for s in sources)
    save_chat(user_id=uid, chat_name=body.chat_name, query=query, answer=full_answer)

    return {
        "answer": full_answer,
        "decision": decision,
        "confidence": confidence,
        "sources": sources,
        "ranking": [{"name": n, "score": round(s, 3)} for n, s in ranking],
    }