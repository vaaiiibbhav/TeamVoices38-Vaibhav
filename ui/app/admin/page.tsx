"use client";

import { useEffect, useMemo, useState } from "react";
import type { Ticket } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const DEPARTMENTS = [
  "Examination Cell",
  "Academic Office",
  "Hostel Administration",
  "Accounts & Finance",
  "Placement Cell",
  "Library",
  "Student Services",
];
const PRIORITIES = ["URGENT", "HIGH", "MEDIUM", "LOW"] as const;
const STATUSES = ["open", "in_progress", "resolved", "closed"];

const PRIORITY_VARIANT: Record<string, "destructive" | "default" | "secondary" | "outline"> = {
  URGENT: "destructive",
  HIGH: "default",
  MEDIUM: "secondary",
  LOW: "outline",
};

function formatCountdown(slaDueAt: string, now: number, status: string): { text: string; className: string } {
  const diffMs = new Date(slaDueAt).getTime() - now;
  const closed = status === "resolved" || status === "closed";
  const overdue = diffMs < 0;

  const abs = Math.abs(diffMs);
  const hours = Math.floor(abs / 3_600_000);
  const days = Math.floor(hours / 24);
  const mins = Math.floor((abs % 3_600_000) / 60_000);
  const label = days > 0 ? `${days}d ${hours % 24}h` : `${hours}h ${mins}m`;

  if (closed) {
    return { text: overdue ? `closed (was ${label} late)` : `closed`, className: "text-muted-foreground" };
  }
  if (overdue) {
    return { text: `OVERDUE by ${label}`, className: "text-red-600 font-semibold" };
  }
  if (diffMs < 2 * 3_600_000) {
    return { text: `${label} left`, className: "text-amber-600 font-semibold" };
  }
  return { text: `${label} left`, className: "text-muted-foreground" };
}

export default function AdminTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [department, setDepartment] = useState("");
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (department) params.set("department", department);
    if (priority) params.set("priority", priority);
    if (status) params.set("status", status);

    setLoading(true);
    setError(null);
    fetch(`/api/admin/tickets?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
      })
      .then(setTickets)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [department, priority, status]);

  const filterSelectClass =
    "rounded-md border bg-background px-2 py-1 text-sm";

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Ticket Queue</h1>

      <div className="mb-4 flex gap-3">
        <select className={filterSelectClass} value={department} onChange={(e) => setDepartment(e.target.value)}>
          <option value="">All departments</option>
          {DEPARTMENTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select className={filterSelectClass} value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <select className={filterSelectClass} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-600">{error}</p>}
      {loading && <p className="text-muted-foreground">Loading...</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{tickets.length} ticket{tickets.length === 1 ? "" : "s"}</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-muted-foreground">
                <th className="py-2 pr-2">Subject</th>
                <th className="py-2 pr-2">Department</th>
                <th className="py-2 pr-2">Priority</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2 pr-2">SLA</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => {
                const sla = formatCountdown(t.sla_due_at, now, t.status);
                return (
                  <tr key={t.id} className="border-b last:border-0">
                    <td className="py-2 pr-2">{t.subject}</td>
                    <td className="py-2 pr-2">{t.department}</td>
                    <td className="py-2 pr-2">
                      <Badge variant={PRIORITY_VARIANT[t.priority] ?? "outline"}>{t.priority}</Badge>
                    </td>
                    <td className="py-2 pr-2">{t.status}</td>
                    <td className={cn("py-2 pr-2", sla.className)}>{sla.text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!loading && tickets.length === 0 && (
            <p className="py-4 text-muted-foreground">No tickets match these filters.</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
