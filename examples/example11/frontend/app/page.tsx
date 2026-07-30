"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
type Thread = { thread_id: string; latest_message_timestamp: string; message_count: number };
type ChatMessage = { role: "user" | "assistant"; content: string; timestamp: string | null };

async function apiRequest(path: string, options?: RequestInit) {
  const response = await fetch(`${apiUrl}${path}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "The chatbot request failed.");
  return body;
}

export default function Chatbot() {
  const [username, setUsername] = useState("user1");
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [isLoadingThread, setIsLoadingThread] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isWaitingForFirstToken, setIsWaitingForFirstToken] = useState(false);
  const [notice, setNotice] = useState("");
  const chatEnd = useRef<HTMLDivElement>(null);

  const loadThreads = async (userId = username) => {
    setIsLoadingThreads(true);
    try { setThreads(await apiRequest(`/api/users/${encodeURIComponent(userId)}/threads?limit=10`)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Unable to load threads."); }
    finally { setIsLoadingThreads(false); }
  };
  useEffect(() => { loadThreads(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, isSending]);

  const applyUsername = () => {
    setThreadId(""); setThreads([]); setMessages([]); setQuestion(""); setNotice(""); loadThreads();
  };
  const createThread = async () => {
    try {
      const data = await apiRequest(`/api/users/${encodeURIComponent(username)}/threads`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      setThreadId(data.thread_id); setMessages([]); setNotice("New thread ready. Start with your first question.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to create thread."); }
  };
  const resumeThread = async (selectedThreadId: string) => {
    setIsLoadingThread(true); setThreadId(selectedThreadId); setMessages([]); setNotice("");
    try {
      const data = await apiRequest(`/api/users/${encodeURIComponent(username)}/threads/${selectedThreadId}`);
      setMessages(data.messages);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to resume thread."); }
    finally { setIsLoadingThread(false); }
  };
  const sendQuestion = async (event: FormEvent) => {
    event.preventDefault(); if (!threadId || !question.trim() || isSending) return;
    const askedQuestion = question.trim(); setQuestion(""); setIsSending(true); setIsWaitingForFirstToken(true); setNotice("");
    setMessages((current) => [...current, { role: "user", content: askedQuestion, timestamp: null }, { role: "assistant", content: "", timestamp: null }]);
    try {
      const response = await fetch(`${apiUrl}/api/users/${encodeURIComponent(username)}/threads/${threadId}/questions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: askedQuestion }) });
      if (!response.ok || !response.body) throw new Error("Unable to start the answer stream.");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let streamError = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n"); buffer = events.pop() || "";
        for (const item of events) {
          const event = item.match(/^event: (.+)$/m)?.[1]; const data = item.match(/^data: (.+)$/m)?.[1];
          if (!event || !data) continue;
          const payload = JSON.parse(data);
          if (event === "token") { setIsWaitingForFirstToken(false); setMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, content: message.content + payload.text } : message)); }
          if (event === "error") streamError = payload.detail || "Unable to get an answer.";
        }
      }
      if (streamError) throw new Error(streamError);
      await loadThreads();
    } catch (error) {
      setMessages((current) => current.slice(0, -2));
      setQuestion(askedQuestion); setNotice(error instanceof Error ? error.message : "Unable to get an answer.");
    } finally { setIsSending(false); setIsWaitingForFirstToken(false); }
  };

  return <main className="app-shell"><aside className="sidebar"><div className="brand"><span>✦</span> Thread Chat</div><div className="user-controls"><label htmlFor="username">Username</label><div className="user-row"><input id="username" value={username} onChange={(event) => setUsername(event.target.value)} /><button onClick={applyUsername} disabled={isLoadingThreads}>Apply</button></div><button className="new-thread" onClick={createThread}>＋ New thread</button></div><div className="thread-nav"><div className="thread-nav-title"><span>Recent threads</span>{isLoadingThreads && <span className="mini-spinner" aria-label="Loading threads" />}</div>{threads.length === 0 && !isLoadingThreads && <p className="empty-sidebar">No populated threads yet.</p>}{threads.map((thread) => <button className={`thread-row ${thread.thread_id === threadId ? "selected" : ""}`} onClick={() => resumeThread(thread.thread_id)} key={thread.thread_id}><span className="thread-name">{thread.thread_id}</span><span className="thread-meta">{thread.message_count} messages</span></button>)}</div><p className="sidebar-foot">Oracle Agent Memory<br />Example 11</p></aside><section className="chat"><header className="chat-header"><div><p className="eyebrow">ORACLE AGENT MEMORY</p><h1>{threadId ? "Thread chat" : "Start a thread"}</h1></div>{threadId && <span className="thread-badge">{threadId}</span>}</header>{notice && <div className="notice">{notice}</div>}<div className="messages" aria-live="polite">{!threadId && <div className="welcome"><div className="welcome-icon">✦</div><h2>How can I help?</h2><p>Create a thread, then ask a question. Resume any recent thread from the sidebar.</p></div>}{isLoadingThread && <div className="loading"><span className="spinner" />Resuming thread…</div>}{messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="avatar">{message.role === "user" ? username.slice(0, 1).toUpperCase() : "✦"}</div><div className="message-content">{message.role === "assistant" ? message.content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : isWaitingForFirstToken ? <div className="waiting"><span className="spinner" />Thinking…</div> : null : <p>{message.content}</p>}</div></article>)}<div ref={chatEnd} /></div><form className="composer" onSubmit={sendQuestion}><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} disabled={!threadId || isSending} placeholder={threadId ? "Message the chatbot…" : "Create or resume a thread to start"} rows={1} /><button disabled={!threadId || !question.trim() || isSending} aria-label="Send question">↑</button></form><p className="composer-help">The model uses this thread&apos;s Context Card and its pretrained knowledge. No RAG or web search.</p></section></main>;
}
