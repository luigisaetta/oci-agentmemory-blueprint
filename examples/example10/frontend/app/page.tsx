"use client";

import { FormEvent, useEffect, useState } from "react";
import "./styles.css";

const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type View = "threads" | "thread" | "search";
type Thread = { thread_id: string; latest_message_timestamp: string };
type Message = { role: string; content: string; timestamp: string };
type SearchResult = Message & { thread_id: string };

async function request(path: string, options?: RequestInit) {
  const response = await fetch(`${api}${path}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Request failed.");
  return body;
}

function XmlElement({ element }: { element: Element }) {
  const attributes = Array.from(element.attributes)
    .map((attribute) => `${attribute.name}="${attribute.value}"`)
    .join(" ");
  const children = Array.from(element.childNodes).filter(
    (node) => node.nodeType === Node.ELEMENT_NODE || node.textContent?.trim()
  );
  return (
    <details className="xml-element" open>
      <summary>
        <span className="xml-tag">&lt;{element.tagName}{attributes ? ` ${attributes}` : ""}&gt;</span>
      </summary>
      <div className="xml-children">
        {children.map((node, index) =>
          node.nodeType === Node.ELEMENT_NODE ? (
            <XmlElement element={node as Element} key={`${node.nodeName}-${index}`} />
          ) : (
            <p className="xml-text" key={`text-${index}`}>{node.textContent?.trim()}</p>
          )
        )}
      </div>
    </details>
  );
}

function ContextCard({ content }: { content: string }) {
  const document = new DOMParser().parseFromString(content, "application/xml");
  if (document.querySelector("parsererror")) {
    return <pre className="context-raw">{content}</pre>;
  }
  return <div className="context-tree"><XmlElement element={document.documentElement} /></div>;
}

export default function Console() {
  const [view, setView] = useState<View>("threads");
  const [user, setUser] = useState("user1");
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selected, setSelected] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [content, setContent] = useState("");
  const [role, setRole] = useState("user");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [insights, setInsights] = useState({ summary: "", context_card: "" });
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [notice, setNotice] = useState("");

  const loadThreads = async () => {
    setIsLoadingThreads(true);
    try {
      const data = await request(`/api/users/${encodeURIComponent(user)}/threads`);
      setThreads(data);
      setNotice(data.length ? "" : "No populated threads found for this user.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to load threads."); }
    finally { setIsLoadingThreads(false); }
  };
  const selectThread = async (threadId: string) => {
    setSelected(threadId); setView("thread"); setInsights({ summary: "", context_card: "" });
    setIsLoadingMessages(true);
    try { setMessages(await request(`/api/users/${encodeURIComponent(user)}/threads/${threadId}/messages`)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Unable to load messages."); }
    finally { setIsLoadingMessages(false); }
  };
  useEffect(() => { loadThreads(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const createThread = async () => {
    try {
      const data = await request(`/api/users/${encodeURIComponent(user)}/threads`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      setSelected(data.thread_id); setMessages([]); setView("thread"); setNotice("Thread created. Add its first message to make it visible in Recent threads.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to create thread."); }
  };
  const addMessage = async (event: FormEvent) => {
    event.preventDefault(); if (!selected || !content.trim()) return;
    try {
      await request(`/api/users/${encodeURIComponent(user)}/threads/${selected}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role, content }) });
      setContent(""); await loadThreads(); await selectThread(selected);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to add message."); }
  };
  const generateInsights = async () => {
    setIsGenerating(true);
    try { setInsights(await request(`/api/users/${encodeURIComponent(user)}/threads/${selected}/insights`)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Unable to generate insights."); }
    finally { setIsGenerating(false); }
  };
  const search = async (event: FormEvent) => {
    event.preventDefault(); if (!query.trim()) return;
    setIsSearching(true); setResults([]);
    try { setResults(await request(`/api/users/${encodeURIComponent(user)}/messages/search?q=${encodeURIComponent(query)}`)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Unable to search messages."); }
    finally { setIsSearching(false); }
  };
  const applyUserScope = () => {
    setSelected(""); setThreads([]); setMessages([]); setInsights({ summary: "", context_card: "" });
    setResults([]); setQuery(""); setContent(""); setNotice(""); loadThreads();
  };
  return <main><aside><div className="brand">◈ Memory<br /><small>Console</small></div>
    {(["threads", "thread", "search"] as View[]).map((item) => <button className={view === item ? "nav-active" : ""} onClick={() => setView(item)} key={item}>{item === "threads" ? "Recent threads" : item === "thread" ? "Thread" : "Search messages"}</button>)}
    <div className="scope"><label>User scope</label><input value={user} onChange={(event) => setUser(event.target.value)} /><button onClick={applyUserScope} disabled={isLoadingThreads}>Apply scope</button></div></aside>
    <section><header><div><p className="eyebrow">ORACLE AGENT MEMORY</p><h1>{view === "threads" ? "Recent threads" : view === "thread" ? "Thread workspace" : "Scoped message search"}</h1></div><button className="primary" onClick={createThread}>+ New thread</button></header>{notice && <p className="notice">{notice}</p>}
      {view === "threads" && <article className="panel"><h2>Threads for {user}</h2>{isLoadingThreads ? <p className="loading"><span className="spinner dark" aria-hidden="true" />Loading threads…</p> : <table><thead><tr><th>Thread</th><th>Last message</th></tr></thead><tbody>{threads.map((thread) => <tr onClick={() => selectThread(thread.thread_id)} key={thread.thread_id}><td>{thread.thread_id}</td><td>{new Date(thread.latest_message_timestamp).toLocaleString()}</td></tr>)}</tbody></table>}</article>}
      {view === "thread" && <article className="panel"><h2>{selected ? `Thread ${selected}` : "Select or create a thread"}</h2>{isLoadingMessages ? <p className="loading"><span className="spinner dark" aria-hidden="true" />Loading messages…</p> : <div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><b>{message.role}</b><p>{message.content}</p></div>)}</div>}<form onSubmit={addMessage}><select value={role} onChange={(event) => setRole(event.target.value)}><option>user</option><option>assistant</option></select><input value={content} onChange={(event) => setContent(event.target.value)} placeholder="Write a message…" /><button className="primary">Send</button></form>{selected && <div className="insights"><button className="primary" onClick={generateInsights} disabled={isGenerating}>{isGenerating ? <><span className="spinner" aria-hidden="true" />Generating insights…</> : "Generate Summary & Context Card"}</button>{isGenerating && <p className="generating">Creating a summary and structured Context Card from this thread…</p>}{insights.summary && <><h3>Summary</h3><p>{insights.summary}</p><h3>Context Card</h3><ContextCard content={insights.context_card} /></>}</div>}</article>}
      {view === "search" && <article className="panel"><h2>Search only {user}&apos;s messages</h2><form onSubmit={search}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this user's messages" /><button className="primary" disabled={isSearching}>{isSearching ? <><span className="spinner" aria-hidden="true" />Searching…</> : "Search"}</button></form>{isSearching && <p className="loading">Searching the selected user&apos;s messages…</p>}{results.map((result, index) => <div className="result" key={index}><b>{result.role}</b> · {result.content}<small>{result.thread_id}</small></div>)}</article>}
    </section></main>;
}
