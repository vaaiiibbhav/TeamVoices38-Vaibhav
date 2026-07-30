"use client";

import { useState } from "react";
import type { InspectorPayload } from "@/lib/types";
import { ConfidenceGauge } from "@/components/confidence-gauge";
import { SourceCards } from "@/components/source-cards";
import { PathBreadcrumbs } from "@/components/path-breadcrumbs";
import { Guardrails } from "@/components/guardrails";
import { ConversationContext } from "@/components/conversation-context";

type ChatResponse = {
  answer: string | null;
  inspector: InspectorPayload;
};

export default function DevChat() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await fetch("/api/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResponse(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <form onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a policy question..."
          style={{ width: "100%", padding: "0.5rem" }}
        />
        <button type="submit" disabled={loading || !message}>
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {response && (
        <div style={{ marginTop: "1rem" }}>
          <p>{response.answer}</p>

          <ConfidenceGauge
            confidence={response.inspector.confidence}
            breakdown={response.inspector.breakdown}
            nextStepHint={response.inspector.next_step_hint}
          />
          <SourceCards sources={response.inspector.sources} />
          <PathBreadcrumbs path={response.inspector.path} />
          <ConversationContext context={response.inspector.slots} />
          <Guardrails reasonCodes={response.inspector.reason_codes} />
        </div>
      )}
    </main>
  );
}
