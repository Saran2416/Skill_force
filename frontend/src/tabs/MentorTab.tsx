import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { AppState, ChatResponse } from "../types";
import { Alert, Card } from "../components/ui";

interface Props {
  state: AppState;
  explanation: string;
  onDone: (resp: ChatResponse) => void;
  clearFlash: () => void;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Minimal markdown-ish rendering: **bold** plus preserved newlines. */
function Markdownish({ text }: { text: string }) {
  const html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, '<code class="rounded bg-[var(--sf-border)] px-1">$1</code>');
  return (
    <div
      className="whitespace-pre-wrap text-sm leading-relaxed"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export default function MentorTab({ state, explanation, onDone, clearFlash }: Props) {
  const profile = state.profile;
  const targetRole = profile.target_role || "your target career";
  const targetCompany = profile.target_company;
  const welcome = useMemo(
    () =>
      `Hello ${profile.name || "there"}! I am your SkillForce mentor. ` +
      `I'm here to help you navigate your journey toward becoming a **${targetRole}` +
      `${targetCompany ? ` at ${targetCompany}` : ""}**. ` +
      "Ask me about closing skill gaps, preparing for technical interviews, or prioritizing roadmap tasks!",
    [profile.name, targetRole, targetCompany],
  );

  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: welcome },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the welcome message in sync when the target role/company changes.
  useEffect(() => {
    setMessages((prev) => {
      if (
        prev.length > 0 &&
        prev[0].role === "assistant" &&
        prev[0].content.includes("I am your SkillForce mentor.") &&
        prev[0].content !== welcome
      ) {
        return [{ ...prev[0], content: welcome }, ...prev.slice(1)];
      }
      return prev;
    });
  }, [welcome]);

  const send = async () => {
    const message = input.trim();
    if (!message || busy) return;
    clearFlash();
    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setBusy(true);
    try {
      const resp = await api.post<ChatResponse>("/mentor/chat", { message });
      setMessages((prev) => [...prev, { role: "assistant", content: resp.reply }]);
      onDone(resp);
      if (resp.error) setError(resp.error);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to communicate with mentor.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="sf-animate max-w-4xl space-y-5">
      <div>
        <h2 className="text-xl">SkillForce Career Mentor</h2>
        <p className="sf-muted">
          Get guidance tailored to your profile, target role, and latest progress.
        </p>
      </div>

      <div>
        <h3 className="text-base">💡 Latest System &amp; Progress Explanation</h3>
        <Card className="mt-2 p-4 text-sm leading-relaxed">
          {explanation || "Save your profile or complete an assessment to see plan changes here."}
        </Card>
      </div>

      <hr className="border-[var(--sf-border)]" />

      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base">💬 Chat with Mentor</h3>
        <button
          className="sf-btn px-3 py-1.5 text-xs"
          onClick={() => {
            setMessages([{ role: "assistant", content: welcome }]);
            setError(null);
          }}
        >
          Clear chat
        </button>
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      <div className="space-y-3">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-[var(--sf-accent)] text-white"
                  : "border border-[var(--sf-border)] bg-[var(--sf-surface-strong)]"
              }`}
            >
              <Markdownish text={msg.content} />
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="sf-muted rounded-2xl border border-[var(--sf-border)] bg-[var(--sf-surface-strong)] px-4 py-3 text-sm">
              Mentor is reviewing your profile and formulating advice…
            </div>
          </div>
        )}
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          className="sf-input flex-1"
          placeholder="Ask a question about your learning plan, interview rounds, or skills..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="sf-btn sf-btn-primary" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
