"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
};

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeNotFoundMessage(detail: unknown): string {
  const raw = typeof detail === "string" ? detail : "Not found";

  // Enforce consistent, friendly messages for common 404 cases
  const s = raw.trim().toLowerCase();
  if (s.includes("translation not found")) return "Translation not found";
  if (s.includes("book not found")) return "Book not found";
  if (s.includes("chapter not found")) return "Chapter not found";
  if (s.includes("verse not found")) return "Verse not found";

  // Generic fallback: keep server message but ensure it ends with "not found" if appropriate
  if (s.endsWith("not found")) {
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }
  return raw;
}

async function readFastApiError(res: Response): Promise<string> {
  // FastAPI commonly returns: { "detail": "..." }
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (data && "detail" in data) {
      return normalizeNotFoundMessage(data.detail);
    }
  } catch {
    // ignore JSON parse errors
  }
  return `Request failed (${res.status})`;
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: "assistant",
      content:
        "Hi! Ask me anything for Bible study—passages, themes, context, or application.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
    []
  );

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isSending]);

  async function sendMessage() {
    const prompt = input.trim();
    if (!prompt || isSending) return;

    setError(null);
    setIsSending(true);

    const userMsg: ChatMessage = { id: uid(), role: "user", content: prompt };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!res.ok) {
        const msg = await readFastApiError(res);
        const assistantMsg: ChatMessage = { id: uid(), role: "assistant", content: msg };
        setMessages((prev) => [...prev, assistantMsg]);
        return;
      }

      const data: { answer: string } = await res.json();

      const assistantMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: data.answer ?? "",
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setError("Could not reach the server. Is the backend running?");
      const assistantMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: "Server unreachable.",
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">
      <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 pb-28 pt-10">
        <header className="mb-6">
          <h1 className="text-xl font-semibold">Bible Study Chat</h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Ask a question. You’ll get an answer with verse citations.
          </p>
        </header>

        <section className="flex-1 space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ring-1 ${
                  m.role === "user"
                    ? "bg-zinc-900 text-white ring-zinc-900 dark:bg-zinc-100 dark:text-black dark:ring-zinc-100"
                    : "bg-white text-zinc-900 ring-zinc-200 dark:bg-zinc-950 dark:text-zinc-100 dark:ring-zinc-800"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl bg-white px-4 py-3 text-sm text-zinc-600 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-950 dark:text-zinc-400 dark:ring-zinc-800">
                Thinking…
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </section>

        <div className="fixed inset-x-0 bottom-0 bg-gradient-to-t from-zinc-50 via-zinc-50 to-transparent px-4 pb-6 pt-6 dark:from-black dark:via-black">
          <div className="mx-auto w-full max-w-3xl">
            {error && (
              <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </div>
            )}

            <div className="flex items-end gap-2 rounded-2xl bg-white p-2 shadow-lg ring-1 ring-zinc-200 dark:bg-zinc-950 dark:ring-zinc-800">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a Bible study question…"
                className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl bg-transparent px-3 py-2 text-sm outline-none placeholder:text-zinc-400"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void sendMessage();
                  }
                }}
                disabled={isSending}
              />

              <button
                onClick={() => void sendMessage()}
                disabled={isSending || !input.trim()}
                className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-black"
                aria-label="Send message"
              >
                Send
              </button>
            </div>

            <p className="mt-2 text-center text-xs text-zinc-500 dark:text-zinc-500">
              Press Enter to send • Shift+Enter for a new line
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
