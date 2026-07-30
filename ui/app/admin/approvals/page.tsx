"use client";

import { useEffect, useState } from "react";
import type { PendingProposal } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminApprovals() {
  const [proposals, setProposals] = useState<PendingProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function reload() {
    setLoading(true);
    setError(null);
    return fetch("/api/approvals")
      .then((res) => {
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
      })
      .then(setProposals)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleDecision(proposalId: string, approved: boolean) {
    setBusyId(proposalId);
    setError(null);
    try {
      const decideRes = await fetch(`/api/approvals/${proposalId}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      if (!decideRes.ok) throw new Error(`decide failed: ${decideRes.status}`);

      if (approved) {
        const executeRes = await fetch(`/api/approvals/${proposalId}/execute`, {
          method: "POST",
        });
        if (!executeRes.ok) throw new Error(`execute failed: ${executeRes.status}`);
      }
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Approval Inbox</h1>

      {error && <p className="text-red-600">{error}</p>}
      {loading && <p className="text-muted-foreground">Loading...</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {proposals.length} pending proposal{proposals.length === 1 ? "" : "s"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-muted-foreground">
                <th className="py-2 pr-2">Action</th>
                <th className="py-2 pr-2">Risk</th>
                <th className="py-2 pr-2">Payload</th>
                <th className="py-2 pr-2">Proposed</th>
                <th className="py-2 pr-2">Decision</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.proposal_id} className="border-b last:border-0">
                  <td className="py-2 pr-2">{p.action_type}</td>
                  <td className="py-2 pr-2">
                    <Badge variant={p.risk_tier === "HIGH" ? "destructive" : "secondary"}>
                      {p.risk_tier}
                    </Badge>
                  </td>
                  <td className="py-2 pr-2 font-mono text-xs">
                    {JSON.stringify(p.payload)}
                  </td>
                  <td className="py-2 pr-2">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-2">
                    <div className="flex gap-2">
                      <button
                        className="rounded-md border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                        disabled={busyId === p.proposal_id}
                        onClick={() => handleDecision(p.proposal_id, true)}
                      >
                        {busyId === p.proposal_id ? "Working..." : "Approve"}
                      </button>
                      <button
                        className="rounded-md border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                        disabled={busyId === p.proposal_id}
                        onClick={() => handleDecision(p.proposal_id, false)}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && proposals.length === 0 && (
            <p className="py-4 text-muted-foreground">No proposals pending approval.</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
