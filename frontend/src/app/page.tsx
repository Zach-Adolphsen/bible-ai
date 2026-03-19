"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type ChatRole = "user" | "assistant";
type ChatMessage = { id: string; role: ChatRole; content: string };

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeNotFoundMessage(detail: unknown): string {
  const raw = typeof detail === "string" ? detail : "Not found";
  const s = raw.trim().toLowerCase();
  if (s.includes("translation not found")) return "Translation not found";
  if (s.includes("book not found")) return "Book not found";
  if (s.includes("chapter not found")) return "Chapter not found";
  if (s.includes("verse not found")) return "Verse not found";
  if (s.endsWith("not found"))
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  return raw;
}

async function readFastApiError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (data && "detail" in data) return normalizeNotFoundMessage(data.detail);
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status})`;
}

function getPrefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function BookIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  );
}

function TypingDots() {
  return (
    <span
      style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}
      aria-label="Thinking"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            display: "block",
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "#6b7280",
            animation: `typingBounce 1.2s ease-in-out ${i * 0.18}s infinite`,
          }}
        />
      ))}
    </span>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: "assistant",
      content:
        "Hello! I'm here to help with your Bible study. Ask me about passages, themes, historical context, or how to apply Scripture to your life.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    [],
  );
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const prefersReducedMotionRef = useRef(false);

  useEffect(() => {
    prefersReducedMotionRef.current = getPrefersReducedMotion();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: prefersReducedMotionRef.current ? "auto" : "smooth",
      block: "end",
    });
  }, [messages.length, isSending]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 176)}px`;
  }, [input]);

  async function sendMessage() {
    const prompt = input.trim();
    if (!prompt || isSending) return;
    setError(null);
    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: prompt },
    ]);
    setInput("");
    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) {
        const msg = await readFastApiError(res);
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: "assistant", content: msg },
        ]);
        return;
      }
      const data: { answer: string } = await res.json();
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "assistant", content: data.answer ?? "" },
      ]);
    } catch {
      setError("Could not reach the server. Is the backend running?");
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "assistant", content: "Server unreachable." },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  const canSend = !isSending && input.trim().length > 0;

  /*
   * Color palette rationale (all hard-coded, no Tailwind dark: variants needed):
   *
   *  Page bg      #1a1a1a  — dark charcoal, not pure black (easier on eyes)
   *  Header/dock  #1a1a1a  — matches page exactly → no seam
   *  Surface      #242424  — cards / assistant bubbles, just slightly lifted
   *  Border       #2e2e2e  — subtle separator
   *  User bubble  #2f6fdf  — calm blue accent (readable, not harsh)
   *  Text primary #e8e6e1  — warm off-white (less eye-strain than #fff)
   *  Text muted   #8a8a8a
   *
   *  Font: "Plus Jakarta Sans" — friendly, highly legible, modern.
   *        Loaded from Google Fonts via a <link> injected into <head> equivalent.
   */

  const BG = "#1a1a1a";
  const SURFACE = "#242424";
  const BORDER = "#2e2e2e";
  const ACCENT = "#2f6fdf"; // user bubble
  const TXT = "#e8e6e1"; // primary text
  const TXT_DIM = "#8a8a8a"; // muted text
  const DOCK_BG = "#1e1e1e"; // input box background

  const globalStyles = `
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      background: ${BG} !important;
      color: ${TXT};
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    @keyframes typingBounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
      40%           { transform: translateY(-5px); opacity: 1; }
    }
    @keyframes msgIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .msg-in { animation: msgIn 0.2s ease forwards; }

    textarea { font-family: inherit; }
    textarea::placeholder { color: ${TXT_DIM}; }
    textarea:focus { outline: none; }
    button { font-family: inherit; cursor: pointer; }
  `;

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: globalStyles }} />

      <div
        style={{
          minHeight: "100dvh",
          background: BG,
          color: TXT,
          fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        }}
      >
        <div
          style={{
            maxWidth: 680,
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            minHeight: "100dvh",
            padding: "0 16px",
          }}
        >
          {/* ── Header ── */}
          <header
            style={{
              position: "sticky",
              top: 0,
              zIndex: 10,
              background: BG,
              borderBottom: `1px solid ${BORDER}`,
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "16px 0",
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                flexShrink: 0,
                background: SURFACE,
                border: `1px solid ${BORDER}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: TXT_DIM,
              }}
            >
              <BookIcon />
            </div>
            <div>
              <h1
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: TXT,
                  letterSpacing: "-0.01em",
                }}
              >
                Bible Study Chat
              </h1>
              <p style={{ fontSize: 11.5, color: TXT_DIM, marginTop: 1 }}>
                Passages · Context · Application · Verse citations
              </p>
            </div>
          </header>

          {/* ── Messages ── */}
          <main
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              paddingTop: 24,
              paddingBottom: 200,
              overflowY: "auto",
            }}
            role="log"
            aria-label="Conversation"
            aria-live="polite"
            aria-relevant="additions"
          >
            {messages.map((m) => (
              <div
                key={m.id}
                className="msg-in"
                style={{
                  display: "flex",
                  justifyContent: m.role === "user" ? "flex-end" : "flex-start",
                }}
                role="listitem"
                aria-label={m.role === "user" ? "You" : "Assistant"}
              >
                {m.role === "user" ? (
                  <div
                    style={{
                      maxWidth: "76%",
                      background: ACCENT,
                      color: "#ffffff",
                      borderRadius: "18px 18px 5px 18px",
                      padding: "10px 15px",
                      fontSize: 14.5,
                      lineHeight: 1.65,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {m.content}
                  </div>
                ) : (
                  <div
                    style={{
                      maxWidth: "76%",
                      background: SURFACE,
                      color: TXT,
                      border: `1px solid ${BORDER}`,
                      borderRadius: "18px 18px 18px 5px",
                      padding: "11px 15px",
                      fontSize: 14.5,
                      lineHeight: 1.7,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {m.content}
                  </div>
                )}
              </div>
            ))}

            {isSending && (
              <div
                style={{ display: "flex", justifyContent: "flex-start" }}
                aria-live="polite"
              >
                <div
                  style={{
                    background: SURFACE,
                    border: `1px solid ${BORDER}`,
                    borderRadius: "18px 18px 18px 5px",
                    padding: "14px 16px",
                  }}
                >
                  <TypingDots />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </main>

          {/* ── Input dock ── */}
          <div
            style={{
              position: "fixed",
              bottom: 0,
              left: "50%",
              transform: "translateX(-50%)",
              width: "100%",
              maxWidth: 680,
              padding: "0 16px 20px",
              background: `linear-gradient(to bottom, transparent, ${BG} 36%)`,
            }}
          >
            {error && (
              <div
                style={{
                  marginBottom: 10,
                  padding: "9px 13px",
                  borderRadius: 12,
                  background: "#2d1a19",
                  border: "1px solid #5a2a26",
                  color: "#f5a99b",
                  fontSize: 13,
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                }}
                role="alert"
              >
                <span>⚠</span> {error}
              </div>
            )}

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: 10,
                background: DOCK_BG,
                border: `1px solid ${BORDER}`,
                borderRadius: 18,
                padding: "10px 10px 10px 16px",
                boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
                transition: "border-color 0.15s",
              }}
              onFocusCapture={(e) =>
                (e.currentTarget.style.borderColor = "#4a4a4a")
              }
              onBlurCapture={(e) =>
                (e.currentTarget.style.borderColor = BORDER)
              }
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a Bible study question…"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void sendMessage();
                  }
                }}
                disabled={isSending}
                aria-label="Ask a Bible study question"
                style={{
                  flex: 1,
                  resize: "none",
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  color: TXT,
                  fontSize: 14.5,
                  lineHeight: 1.6,
                  minHeight: 24,
                  maxHeight: 176,
                }}
              />

              <button
                onClick={() => void sendMessage()}
                disabled={!canSend}
                aria-label="Send message"
                style={{
                  width: 36,
                  height: 36,
                  flexShrink: 0,
                  borderRadius: 11,
                  border: "none",
                  background: canSend ? ACCENT : "#2a2a2a",
                  color: canSend ? "#fff" : TXT_DIM,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: canSend ? "pointer" : "not-allowed",
                  transition: "background 0.15s, transform 0.1s",
                  marginBottom: 1,
                }}
                onMouseEnter={(e) => {
                  if (canSend) e.currentTarget.style.background = "#2560c8";
                }}
                onMouseLeave={(e) => {
                  if (canSend) e.currentTarget.style.background = ACCENT;
                }}
                onMouseDown={(e) => {
                  if (canSend) e.currentTarget.style.transform = "scale(0.93)";
                }}
                onMouseUp={(e) => {
                  e.currentTarget.style.transform = "scale(1)";
                }}
              >
                <SendIcon />
              </button>
            </div>

            <p
              style={{
                marginTop: 8,
                textAlign: "center",
                fontSize: 11,
                color: "#555",
              }}
            >
              <span style={{ fontWeight: 600, color: "#666" }}>Enter</span> to
              send ·{" "}
              <span style={{ fontWeight: 600, color: "#666" }}>
                Shift + Enter
              </span>{" "}
              for a new line
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
