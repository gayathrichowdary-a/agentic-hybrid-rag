"use client";
import { useCallback, useEffect, useMemo, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(API + path, { method, headers, body: form || (body && JSON.stringify(body)) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Try again.");
    err.status = res.status;
    throw err;
  }
  return data;
}

const NAV = [
  ["home", "🏠 Home"],
  ["upload", "📁 Upload Documents"],
  ["chat", "💬 Chat"],
  ["compare", "⚖️ Compare Documents"],
  ["graph", "🕸️ Knowledge Graph"],
  ["memory", "🧠 Memory"],
  ["history", "🕘 History"],
  ["settings", "⚙️ Settings"],
];

// Upload dropdown choices. The backend reads the tier number from the text, so keep "Tier 1/2/3" at the start.
const TIERS = [
  "Tier 1 (Authoritative / Regulatory Policy)",
  "Tier 2 (Internal Verified / Architecture & Runbooks)",
  "Tier 3 (Informal / Field Notes & Chat Archives)",
];
const DEPARTMENTS = [
  "Legal & InfoSec",
  "DevOps & Infrastructure",
  "Software Engineering",
  "Human Resources",
  "Customer Operations",
];

export default function Page() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("home");
  const [booting, setBooting] = useState(true);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    try { setDark(localStorage.getItem("theme") === "dark"); } catch {}
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch {}
  }, [dark]);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
    setView("home");
  }, []);

  useEffect(() => {
    if (!localStorage.getItem("token")) return setBooting(false);
    api("/me").then(setUser).catch(() => localStorage.removeItem("token")).finally(() => setBooting(false));
  }, []);

  if (booting) return <div className="center muted">Loading…</div>;
  if (!user) return <Auth onLogin={setUser} />;

  const props = { user, logout };
  return (
    <div className="shell">
      <aside className="side">
        <div className="side-top">
          <span className="badge">ENTERPRISE</span>
          <span className="active">● Active</span>
        </div>
        <div className="side-title">Adaptive Multi-Agent RAG</div>
        <div className="usercard">
          <b>👤 {user.full_name || user.username}</b>
          <span>{user.email}</span>
        </div>
        <label className="toggle">
          <input type="checkbox" checked={dark} onChange={(e) => setDark(e.target.checked)} />
          🌙 Dark Mode
        </label>
        <div className="nav-h">🧭 Navigation Menu</div>
        <nav className="nav">
          {NAV.map(([id, label]) => (
            <button key={id} className={view === id ? "on" : ""} onClick={() => setView(id)}>{label}</button>
          ))}
          <button onClick={logout}>🚪 Log out</button>
        </nav>
      </aside>
      <main className="main">
        {view === "home" && <Home {...props} />}
        {view === "upload" && <Upload {...props} />}
        {view === "chat" && <Chat {...props} />}
        {view === "compare" && <Compare {...props} />}
        {view === "graph" && <Graph {...props} />}
        {view === "memory" && <Memory {...props} />}
        {view === "history" && <History {...props} />}
        {view === "settings" && <Settings {...props} />}
      </main>
    </div>
  );
}

function PasswordInput({ value, onChange, placeholder, autoComplete }) {
  const [show, setShow] = useState(false);
  return (
    <div className="pw">
      <input className="input" type={show ? "text" : "password"} placeholder={placeholder} value={value} onChange={onChange} autoComplete={autoComplete} />
      <button type="button" className="eye" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>
        {show ? "🙈" : "👁"}
      </button>
    </div>
  );
}

function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ username: "", email: "", password: "", confirm: "" });
  const [agree, setAgree] = useState(true);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const login = mode === "login";

  function switchMode() {
    setMode(login ? "signup" : "login");
    setMsg({ type: "", text: "" });
  }

  async function submit(e) {
    e.preventDefault();
    setMsg({ type: "", text: "" });
    if (!login) {
      if (f.password !== f.confirm) return setMsg({ type: "err", text: "Passwords do not match." });
      if (!agree) return setMsg({ type: "err", text: "Please accept the Terms of Service to continue." });
    }
    setBusy(true);
    try {
      if (!login) {
        await api("/auth/signup", { method: "POST", body: { ...f, full_name: f.username } });
        setMode("login");
        setMsg({ type: "ok", text: "Account created. Sign in to continue." });
      } else {
        const r = await api("/auth/login", { method: "POST", body: { username: f.username, password: f.password } });
        localStorage.setItem("token", r.token);
        onLogin(r.user);
      }
    } catch (err) {
      setMsg({ type: "err", text: err.message });
    }
    setBusy(false);
  }

  return (
    <div className="auth-wrap">
      <section className="auth-hero">
        <img src={login ? "/images/login_robot.png" : "/images/signup_robot.png"} alt="Friendly AI assistant" />
        {login ? (
          <h2>Smarter Answers, <span className="hl">Faster Insights</span></h2>
        ) : (
          <h2>Intelligent <span className="hl">Workspaces</span></h2>
        )}
        <p className="sub">Enterprise Hybrid RAG Platform</p>
        <hr />
        <div className="chips">
          {(login ? ["Agentic Retrieval", "Reranking", "Multi-Vector Search"] : ["Vector Embeddings", "Automated Routing", "Verified Sources"]).map((c) => (
            <span key={c}>• {c}</span>
          ))}
        </div>
      </section>

      <form className="auth-form" onSubmit={submit}>
        <div className="brand">
          <div className="logo">⚡</div>
          <div>
            <b>Enterprise RAG</b>
            <small>Adaptive Intelligence Knowledge Platform</small>
          </div>
        </div>

        <h1>{login ? "Welcome back" : "Create account"}</h1>
        <p className="muted" style={{ margin: 0 }}>
          {login ? "Enter your credentials to access your enterprise workspace" : "Join the enterprise intelligence knowledge platform"}
        </p>

        <label>
          Username
          <input className="input" placeholder="Enter your username" value={f.username} onChange={set("username")} autoComplete="username" />
        </label>

        {login ? (
          <label>
            Password
            <PasswordInput value={f.password} onChange={set("password")} placeholder="Enter your password" autoComplete="current-password" />
          </label>
        ) : (
          <>
            <label>
              Email
              <input className="input" type="email" placeholder="name@company.com" value={f.email} onChange={set("email")} />
            </label>
            <div className="two">
              <label>
                Password
                <PasswordInput value={f.password} onChange={set("password")} placeholder="Create password" autoComplete="new-password" />
              </label>
              <label>
                Confirm Password
                <PasswordInput value={f.confirm} onChange={set("confirm")} placeholder="Confirm password" autoComplete="new-password" />
              </label>
            </div>
            <label className="check">
              <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
              I agree to the Enterprise Terms of Service and Privacy Policy
            </label>
          </>
        )}

        {msg.text && <div className={msg.type}>{msg.text}</div>}

        <button className="btn block" disabled={busy}>
          {busy ? "Please wait…" : login ? "Sign In" : "Create Account"}
        </button>

        <div className="switch">
          <span>{login ? "Don't have an account?" : "Already have an account?"}</span>
          <button type="button" className="btn outline block" onClick={switchMode}>
            {login ? "Sign up" : "Sign In"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Home({ user, logout }) {
  const [stats, setStats] = useState({ docs: "–", memories: "–", chats: "–" });

  useEffect(() => {
    const fail = (e) => e.status === 401 && logout();
    api("/documents").then((r) => setStats((s) => ({ ...s, docs: r.documents.length }))).catch(fail);
    api("/memory").then((r) => setStats((s) => ({ ...s, memories: r.memories.length }))).catch(fail);
    api("/chats")
      .then((r) => setStats((s) => ({ ...s, chats: Object.values(r.chats).filter((m) => m.length).length })))
      .catch(fail);
  }, [logout]);

  const name = user.full_name || user.username;

  return (
    <>
      <h1 className="page-title">🛡️ Adaptive Multi-Agent Enterprise RAG</h1>
      <p className="page-sub">Next-Generation Knowledge Intelligence with Hybrid Retrieval, Knowledge Graph &amp; Web Search</p>

      <div className="hero-card">
        <div>
          <h2>Welcome back, {name}! 👋</h2>
          <p>
            Your adaptive multi-agent knowledge mesh is fully operational. Ready to ingest documents, traverse knowledge
            subgraphs, and verify grounded reasoning.
          </p>
        </div>
        <img src="/images/dashboard_robot.png" alt="AI assistant" />
      </div>

      <div className="stats">
        <div className="stat"><b>{stats.docs}</b><span>Active Documents</span></div>
        <div className="stat"><b>{stats.chats}</b><span>Conversations</span></div>
        <div className="stat"><b>{stats.memories}</b><span>Saved Memories</span></div>
        <div className="stat"><b>LangGraph</b><span>Query Router</span></div>
      </div>

      <h2 className="sec-title">🔄 Multi-Agent Orchestration Architecture (LangGraph)</h2>
      <p className="muted">Each question is routed to the best source, then answered from what was found.</p>
      <div className="flow">
        <span className="node">Your question</span><span className="arrow">→</span>
        <span className="node hot">LangGraph router</span><span className="arrow">→</span>
        <span className="node">Vector search</span><span className="arrow">+</span>
        <span className="node">Knowledge graph</span><span className="arrow">+</span>
        <span className="node">Memory</span><span className="arrow">+</span>
        <span className="node">Web search</span><span className="arrow">→</span>
        <span className="node hot">Answer</span>
      </div>

      <h2 className="sec-title">⚡ Core Architectural Pillars</h2>
      <div className="pillars">
        <div className="pillar"><h3>Vector Search</h3><p>Embeds your documents with sentence-transformers and finds matches with a FAISS index.</p></div>
        <div className="pillar"><h3>Knowledge Graph</h3><p>Links entities across your files so answers can follow relationships, not just keywords.</p></div>
        <div className="pillar"><h3>Long-Term Memory</h3><p>Remembers useful facts from your chats and brings them back when they matter.</p></div>
        <div className="pillar"><h3>Web Search</h3><p>Falls back to Tavily web search when your documents do not hold the answer.</p></div>
      </div>
      <p className="muted" style={{ marginTop: "1.5rem" }}>
        Supported files: PDF, Word, text, CSV, Excel and images (read with OCR). Start on Upload Documents, then open Chat.
      </p>
    </>
  );
}

function Upload({ logout }) {
  const [info, setInfo] = useState({ documents: [], stats: null });
  const [files, setFiles] = useState([]);
  const [tier, setTier] = useState(TIERS[0]);
  const [dept, setDept] = useState(DEPARTMENTS[0]);
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const fail = useCallback((e) => (e.status === 401 ? logout() : setError(e.message)), [logout]);
  const load = useCallback(() => api("/documents/details").then(setInfo).catch(fail), [fail]);
  useEffect(() => { load(); }, [load]);

  async function upload() {
    setBusy(true); setError(""); setResults([]);
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("tier", tier);
    form.append("department", dept);
    try { setResults((await api("/documents", { method: "POST", form })).results); setFiles([]); await load(); }
    catch (e) { fail(e); }
    setBusy(false);
  }

  async function clearAll() {
    if (!confirm("Remove all your uploaded documents?")) return;
    try { await api("/documents", { method: "DELETE" }); setResults([]); load(); } catch (e) { fail(e); }
  }

  const { documents: docs, stats } = info;

  return (
    <>
      <h1>📁 Upload Documents &amp; Assign Source Authority</h1>
      <p className="muted">Ingest documents, assign a Source Authority Tier and department, and see how they are indexed. PDF, DOCX, TXT, CSV, XLSX, PNG or JPG, up to 10 MB each. Please don’t upload passwords or bank details.</p>

      <div className="kpis">
        <div className="kpi"><span>Total indexed docs</span><b>{stats ? stats.documents : "–"}</b><small>Your knowledge base</small></div>
        <div className="kpi"><span>Vector chunks</span><b>{stats ? stats.chunks.toLocaleString() : "–"}</b><small>FAISS index</small></div>
        <div className="kpi"><span>Avg source reliability</span><b>{stats && stats.avg_reliability != null ? `${stats.avg_reliability}%` : "–"}</b><small>Set by tier</small></div>
        <div className="kpi"><span>Embedding dimension</span><b>{stats ? `${stats.embedding_dim}d` : "–"}</b><small>{stats ? stats.embedding_model : ""}</small></div>
      </div>

      <div className="card">
        <div className="fields">
          <label className="field">
            <span>Select Source Authority Tier</span>
            <select value={tier} onChange={(e) => setTier(e.target.value)}>
              {TIERS.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Department / Domain</span>
            <select value={dept} onChange={(e) => setDept(e.target.value)}>
              {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
        </div>
        <div className="row">
          <input type="file" multiple accept=".pdf,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg" onChange={(e) => setFiles([...e.target.files])} />
          <button className="btn" disabled={!files.length || busy} onClick={upload}>{busy ? "Indexing… (first upload can take a minute)" : "Upload and index"}</button>
        </div>
        <p className="muted" style={{ margin: ".75rem 0 0" }}>The tier and department you pick here are saved with every file you upload in this batch.</p>
        {error && <div className="err">{error}</div>}
        {results.map((r) => <div key={r.name} className="muted">{r.name}: {r.status}</div>)}
      </div>

      <h2>Your documents</h2>
      {docs.length ? (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr><th>Document</th><th>Authority tier</th><th>Department</th><th>Reliability</th><th>Words</th><th>Chunks</th><th>Uploaded</th></tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.name}>
                  <td>{d.name}</td>
                  <td>{d.tier_short}</td>
                  <td>{d.department}</td>
                  <td>{d.reliability != null ? `${d.reliability}%` : "–"}</td>
                  <td>{d.words ? d.words.toLocaleString() : "–"}</td>
                  <td>{d.chunks || "–"}</td>
                  <td>{d.uploaded || "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="muted">Nothing uploaded yet. Choose files above to get started.</p>}
      {docs.some((d) => d.tier_short === "Not set") && (
        <p className="muted">“Not set” means the file was uploaded before tiers existed. Upload the same file again with a tier to set it.</p>
      )}
      {docs.length > 0 && <p><button className="btn danger" onClick={clearAll}>Remove all documents</button></p>}
    </>
  );
}

function Chat({ logout }) {
  const [chats, setChats] = useState({ "Chat 1": [] });
  const [current, setCurrent] = useState("Chat 1");
  const [docs, setDocs] = useState([]);
  const [doc, setDoc] = useState("All Documents");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState(null);

  const fail = useCallback((e) => (e.status === 401 ? logout() : setError(e.message)), [logout]);

  useEffect(() => {
    api("/chats").then((r) => {
      const names = Object.keys(r.chats);
      if (names.length) { setChats(r.chats); setCurrent(names[0]); }
    }).catch(fail);
    api("/documents").then((r) => setDocs(r.documents)).catch(fail);
  }, [fail]);

  function newChat() {
    let n = Object.keys(chats).length + 1;
    while (chats[`Chat ${n}`]) n++;
    setChats({ ...chats, [`Chat ${n}`]: [] });
    setCurrent(`Chat ${n}`);
    setMeta(null);
  }

  async function removeChat() {
    try { await api(`/chats/${encodeURIComponent(current)}`, { method: "DELETE" }); } catch (e) { return fail(e); }
    const { [current]: _gone, ...rest } = chats;
    const names = Object.keys(rest);
    setChats(names.length ? rest : { "Chat 1": [] });
    setCurrent(names[0] || "Chat 1");
  }

  async function send(e) {
    e.preventDefault();
    const query = input.trim();
    if (!query || busy) return;
    setBusy(true); setError("");
    try {
      const r = await api("/chat", { method: "POST", body: { query, chat_name: current, doc } });
      setChats((c) => ({ ...c, [current]: [...(c[current] || []), { query, answer: r.answer }] }));
      setMeta(r);
      setInput("");
    } catch (err) { fail(err); }
    setBusy(false);
  }

  const messages = chats[current] || [];
  const title = (name) => (chats[name][0] ? chats[name][0].query.slice(0, 28) : name);

  return (
    <>
      <h1>Chat</h1>
      <div className="chat">
        <div className="chats">
          <button className="btn" onClick={newChat}>New chat</button>
          {Object.keys(chats).map((n) => (
            <button key={n} className={n === current ? "on" : ""} onClick={() => { setCurrent(n); setMeta(null); }}>{title(n)}</button>
          ))}
          <button className="btn ghost" onClick={removeChat}>Delete this chat</button>
        </div>
        <div>
          <select value={doc} onChange={(e) => setDoc(e.target.value)} aria-label="Search in">
            <option>All Documents</option>
            {docs.map((d) => <option key={d}>{d}</option>)}
          </select>
          <div className="msgs">
            {!messages.length && <p className="muted">Ask a question about your documents to begin.</p>}
            {messages.map((m, i) => (
              <div key={i} className="msgs" style={{ margin: 0 }}>
                <div className="q">{m.query}</div>
                <div className="a">{m.answer}</div>
              </div>
            ))}
            {busy && <p className="muted">Searching your documents…</p>}
          </div>
          {meta && (
            <p className="meta">
              Route: {meta.decision} · Confidence: {meta.confidence} · Best match: {meta.ranking[0]?.name}
            </p>
          )}
          {error && <div className="err">{error}</div>}
          <form className="row" onSubmit={send}>
            <input className="input" style={{ flex: 1 }} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything about your documents…" />
            <button className="btn" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------- Compare */

// Small Markdown reader for the AI answer: ## headings, - bullets, **bold**. No extra packages needed.
function Md({ text }) {
  const inline = (s) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
      p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={i}>{p.slice(2, -2)}</strong> : p
    );
  const out = [];
  let list = [];
  const flush = () => {
    if (list.length) { out.push(<ul key={`u${out.length}`}>{list.map((t, i) => <li key={i}>{inline(t)}</li>)}</ul>); list = []; }
  };
  text.split("\n").forEach((raw) => {
    const line = raw.trim();
    const h = line.match(/^#{1,6}\s+(.*)$/);
    const li = line.match(/^(?:[-*•]|\d+\.)\s+(.*)$/);
    if (h) { flush(); out.push(<h3 key={`h${out.length}`}>{inline(h[1])}</h3>); }
    else if (li) list.push(li[1]);
    else if (line) { flush(); out.push(<p key={`p${out.length}`}>{inline(line)}</p>); }
    else flush();
  });
  flush();
  return <div className="md">{out}</div>;
}

function Metric({ title, value, hint }) {
  const pct = Math.round(value * 1000) / 10;
  return (
    <div className="metric">
      <div className="metric-card"><span>{title}</span><b>{pct.toFixed(1)}%</b></div>
      <div className="bar" role="img" aria-label={`${title} ${pct.toFixed(1)} percent`}>
        <i style={{ width: `${pct > 0 ? Math.max(pct, 1.5) : 0}%` }} />
      </div>
      <p className="muted">{hint}</p>
    </div>
  );
}

function KeywordBars({ items }) {
  const max = Math.max(1, ...items.flatMap((k) => [k.a, k.b]));
  const w = (n) => `${n > 0 ? Math.max((n / max) * 100, 1) : 0}%`;
  return (
    <div className="kw">
      {items.map((k) => (
        <div className="kw-row" key={k.word}>
          <span className="kw-word">{k.word}</span>
          <div className="kw-bars">
            <div className="kw-bar"><i className="a" style={{ width: w(k.a) }} />{k.a}</div>
            <div className="kw-bar"><i className="b" style={{ width: w(k.b) }} />{k.b}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Compare({ logout }) {
  const [docs, setDocs] = useState(null);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ai, setAi] = useState({ key: "", text: "", busy: false, error: "" });

  useEffect(() => {
    api("/documents")
      .then((r) => { setDocs(r.documents); setA(r.documents[0] || ""); setB(r.documents[1] || ""); })
      .catch((e) => (e.status === 401 ? logout() : setError(e.message)));
  }, [logout]);

  useEffect(() => {
    if (!a || !b) return;
    if (a === b) { setRes(null); setError("Pick two different documents."); return; }
    let live = true;
    setLoading(true); setError("");
    api("/compare", { method: "POST", body: { doc_a: a, doc_b: b } })
      .then((r) => live && setRes(r))
      .catch((e) => { if (!live) return; if (e.status === 401) logout(); else { setRes(null); setError(e.message); } })
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [a, b, logout]);

  const key = `${a}||${b}`;

  async function generate() {
    setAi({ key, text: "", busy: true, error: "" });
    try {
      const r = await api("/compare/ai", { method: "POST", body: { doc_a: a, doc_b: b } });
      setAi({ key, text: r.summary, busy: false, error: "" });
    } catch (e) {
      if (e.status === 401) return logout();
      setAi({ key, text: "", busy: false, error: e.message });
    }
  }

  if (docs === null && !error) return <p className="muted">Loading…</p>;

  const head = (
    <>
      <h1>⚖️ Compare Documents</h1>
      <p className="muted">Pick two of your uploaded documents to see how similar they are and where they differ.</p>
    </>
  );

  if (docs && docs.length < 2) {
    return (
      <>
        {head}
        <div className="card"><p style={{ margin: 0 }}>You need at least two documents to compare. Upload another one on the Upload Documents page.</p></div>
      </>
    );
  }

  const pickers = docs && (
    <div className="picks">
      <label className="field">
        <span>📄 Document A</span>
        <select value={a} onChange={(e) => setA(e.target.value)}>{docs.map((d) => <option key={d}>{d}</option>)}</select>
      </label>
      <label className="field">
        <span>📄 Document B</span>
        <select value={b} onChange={(e) => setB(e.target.value)}>{docs.map((d) => <option key={d}>{d}</option>)}</select>
      </label>
    </div>
  );

  const mine = ai.key === key;

  return (
    <>
      {head}
      {pickers}
      {error && <div className="err">{error}</div>}
      {loading && !res && <p className="muted">Comparing…</p>}

      {res && (
        <div style={{ opacity: loading ? 0.55 : 1 }}>
          <h2 className="sec-title">📊 How similar are they?</h2>
          <p className="verdict">{res.emoji} {res.label}</p>
          {res.note && <p className="muted">{res.note}</p>}
          <div className="metrics">
            <Metric title="Topic similarity" value={res.topic_similarity} hint="How much the two use the same important words, weighted by how often." />
            <Metric title="Vocabulary overlap" value={res.vocabulary_overlap} hint="Share of all distinct words that appear in both." />
            <Metric title="Copied-text overlap" value={res.copied_overlap} hint="Share of identical 5-word sequences. High means shared or copied passages." />
          </div>

          <h2 className="sec-title">📋 The two documents</h2>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th></th><th>Document</th><th>Authority tier</th><th>Reliability</th><th>Words</th><th>Department</th><th>Uploaded</th></tr></thead>
              <tbody>
                {[["A", res.a], ["B", res.b]].map(([tag, d]) => (
                  <tr key={tag}>
                    <td>{tag}</td>
                    <td>{d.name}</td>
                    <td>{d.tier_short}</td>
                    <td>{d.reliability != null ? `${d.reliability}%` : "–"}</td>
                    <td>{d.words ? d.words.toLocaleString() : "–"}</td>
                    <td>{d.department}</td>
                    <td>{d.uploaded || "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="sec-title">🔑 Keywords</h2>
          {res.shared_keywords.length ? (
            <>
              <p><strong>Most important shared words</strong> <span className="muted">(times each appears)</span></p>
              <div className="legend">
                <span><i className="dot a" /> Document A</span>
                <span><i className="dot b" /> Document B</span>
                <span className="muted">{res.shared_count.toLocaleString()} words in common</span>
              </div>
              <KeywordBars items={res.shared_keywords} />
            </>
          ) : <p className="muted">These two documents share no important words.</p>}

          <div className="words">
            <div><p><strong>Only in Document A</strong></p><p>{res.only_a.length ? res.only_a.join(", ") : "—"}</p></div>
            <div><p><strong>Only in Document B</strong></p><p>{res.only_b.length ? res.only_b.join(", ") : "—"}</p></div>
          </div>

          <h2 className="sec-title">🤖 AI comparison</h2>
          <p><button className="btn" onClick={generate} disabled={ai.busy}>{ai.busy ? "Reading both documents…" : mine && ai.text ? "✨ Generate again" : "✨ Generate AI comparison"}</button></p>
          {mine && ai.error && <div className="err">{ai.error}</div>}
          {mine && ai.text && <Md text={ai.text} />}
        </div>
      )}
    </>
  );
}

/* ---------------------------------------------------------- Knowledge Graph */

const NODE_R = { document: 15, tier: 11, department: 11 };
const TYPE_NAME = { document: "Document", tier: "Authority tier", department: "Department", keyword: "Keyword" };
const short = (s, n = 24) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

function Graph({ logout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [kw, setKw] = useState("shared");
  const [sel, setSel] = useState(null);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    api("/graph").then(setData).catch((e) => (e.status === 401 ? logout() : setError(e.message)));
  }, [logout]);

  const view = useMemo(() => {
    if (!data) return null;
    const keep = (n) => n.type !== "keyword" || kw === "all" || (kw === "shared" && n.shared);
    const nodes = data.nodes.filter(keep);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = data.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const near = {};
    edges.forEach((e) => {
      (near[e.source] ||= new Set()).add(e.target);
      (near[e.target] ||= new Set()).add(e.source);
    });
    return { nodes, edges, byId, near };
  }, [data, kw]);

  if (error) return <><h1>🕸️ Knowledge Graph</h1><div className="err">{error}</div></>;
  if (!view) return <><h1>🕸️ Knowledge Graph</h1><p className="muted">Building the graph…</p></>;

  if (!data.nodes.length) {
    return (
      <>
        <h1>🕸️ Knowledge Graph</h1>
        <div className="card"><p style={{ margin: 0 }}>Nothing to draw yet. Upload documents and the graph will show how they connect.</p></div>
      </>
    );
  }

  const X = (n) => 50 + n.x * 900;
  const Y = (n) => 40 + n.y * 540;
  const focus = hover || sel;
  const active = focus && view.byId[focus] ? new Set([focus, ...(view.near[focus] || [])]) : null;
  const picked = sel && view.byId[sel];
  const links = picked ? [...(view.near[sel] || [])].map((id) => view.byId[id]) : [];

  return (
    <>
      <h1>🕸️ Knowledge Graph</h1>
      <p className="muted">
        How your documents connect through their authority tier, department and most important words.
        {" "}{data.stats.documents} documents · {data.stats.keywords} keywords · {data.stats.links} links
      </p>

      <div className="row" style={{ margin: ".75rem 0" }}>
        <label className="field" style={{ minWidth: 240 }}>
          <span>Keywords to show</span>
          <select value={kw} onChange={(e) => { setKw(e.target.value); setSel(null); }}>
            <option value="shared">Only words shared by 2+ documents</option>
            <option value="all">All keywords</option>
            <option value="none">Hide keywords</option>
          </select>
        </label>
        <div className="legend" style={{ margin: 0 }}>
          <span><i className="dot gdoc" /> Document</span>
          <span><i className="dot gtier" /> Tier</span>
          <span><i className="dot gdept" /> Department</span>
          <span><i className="dot gkw" /> Keyword</span>
        </div>
      </div>

      <div className="graph">
        <svg className="graph-svg" viewBox="0 0 1000 620" role="img" aria-label="Knowledge graph of your documents" onClick={() => setSel(null)}>
          {view.edges.map((e, i) => {
            const s = view.byId[e.source], t = view.byId[e.target];
            const hot = active && active.has(e.source) && active.has(e.target) && (e.source === focus || e.target === focus);
            const cls = `ge${e.type === "similar to" ? " similar" : ""}${hot ? " hot" : ""}${active && !hot ? " dim" : ""}`;
            return <line key={i} className={cls} x1={X(s)} y1={Y(s)} x2={X(t)} y2={Y(t)} />;
          })}
          {view.nodes.map((n) => {
            const dim = active && !active.has(n.id);
            const r = n.type === "keyword" ? (n.shared ? 7 : 5) : NODE_R[n.type];
            const labelled = n.type !== "keyword" || n.shared || (active && active.has(n.id));
            return (
              <g
                key={n.id}
                className="gnode"
                tabIndex={0}
                role="button"
                aria-label={`${TYPE_NAME[n.type]}: ${n.label}`}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(n.id)}
                onBlur={() => setHover(null)}
                onClick={(e) => { e.stopPropagation(); setSel(n.id === sel ? null : n.id); }}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSel(n.id === sel ? null : n.id); } }}
              >
                <circle className={`gn ${n.type}${n.shared ? " shared" : ""}${dim ? " dim" : ""}${n.id === sel ? " on" : ""}`} cx={X(n)} cy={Y(n)} r={r} />
                {labelled && (
                  <text className={`gl ${n.type === "keyword" ? "kw" : n.type === "document" ? "doc" : ""}${dim ? " dim" : ""}`} x={X(n)} y={Y(n) + r + 15} textAnchor="middle">
                    {short(n.label, n.type === "document" ? 26 : 22)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        <aside className="card gside">
          {picked ? (
            <>
              <p className="muted" style={{ margin: 0 }}>{TYPE_NAME[picked.type]}</p>
              <h3 style={{ margin: ".15rem 0 .6rem", wordBreak: "break-word" }}>{picked.label}</h3>
              {picked.type === "document" && (
                <p className="muted" style={{ margin: "0 0 .6rem" }}>
                  {picked.tier}{picked.reliability != null ? ` · ${picked.reliability}% reliable` : ""}<br />{picked.department}
                </p>
              )}
              <p style={{ margin: "0 0 .3rem" }}><strong>Connected to {links.length}</strong></p>
              <ul className="gl-list">
                {links.map((n) => (
                  <li key={n.id}><button className="link" onClick={() => setSel(n.id)}>{n.label}</button> <span className="muted">{TYPE_NAME[n.type].toLowerCase()}</span></li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted" style={{ margin: 0 }}>Click a dot to see what it connects to. Hover to highlight its neighbours.</p>
          )}
        </aside>
      </div>
    </>
  );
}

function Memory({ logout }) {
  const [items, setItems] = useState(null);
  useEffect(() => { api("/memory").then((r) => setItems(r.memories)).catch((e) => e.status === 401 && logout()); }, [logout]);
  return (
    <>
      <h1>Memory</h1>
      <p className="muted">Facts the assistant decided are worth remembering from your chats.</p>
      {items === null ? <p className="muted">Loading…</p> : items.length ? <ul>{items.map((m, i) => <li key={i}>{m}</li>)}</ul> : <p className="muted">No memories yet. They appear as you chat.</p>}
    </>
  );
}

function History({ logout }) {
  const [chats, setChats] = useState(null);
  useEffect(() => { api("/chats").then((r) => setChats(r.chats)).catch((e) => e.status === 401 && logout()); }, [logout]);
  return (
    <>
      <h1>History</h1>
      {chats === null ? <p className="muted">Loading…</p> : !Object.keys(chats).length ? <p className="muted">No conversations yet.</p> : Object.entries(chats).map(([name, msgs]) => (
        <details key={name}>
          <summary>{msgs[0]?.query.slice(0, 60) || name}</summary>
          {msgs.map((m, i) => (
            <div key={i} style={{ marginTop: ".75rem" }}>
              <strong>You:</strong> {m.query}
              <div style={{ whiteSpace: "pre-wrap" }}><strong>Assistant:</strong> {m.answer}</div>
            </div>
          ))}
        </details>
      ))}
    </>
  );
}

function Settings({ user, logout }) {
  return (
    <>
      <h1>Settings</h1>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <div><strong>Name:</strong> {user.full_name}</div>
        <div><strong>Username:</strong> {user.username}</div>
        <div><strong>Email:</strong> {user.email}</div>
      </div>
      <button className="btn ghost" onClick={logout}>Log out</button>
    </>
  );
}