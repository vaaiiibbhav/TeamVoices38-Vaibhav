"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Gauge } from "lucide-react";
import { PanelSection } from "./panel-section";

const ANSWER_THRESHOLD = 0.8;
const CLARIFY_THRESHOLD = 0.55;

interface ConfidenceGaugeProps {
  confidence: number;
  breakdown: Record<string, number>;
  nextStepHint: string;
}

function bandColor(confidence: number) {
  if (confidence >= ANSWER_THRESHOLD) return "bg-emerald-500";
  if (confidence >= CLARIFY_THRESHOLD) return "bg-amber-500";
  return "bg-red-500";
}

function bandLabel(confidence: number) {
  if (confidence >= ANSWER_THRESHOLD) return "Answer";
  if (confidence >= CLARIFY_THRESHOLD) return "Clarify";
  return "Triage";
}

export function ConfidenceGauge({
  confidence,
  breakdown,
  nextStepHint,
}: ConfidenceGaugeProps) {
  const pct = Math.round(confidence * 100);

  return (
    <PanelSection
      title="Confidence"
      icon={<Gauge className="h-4 w-4 text-blue-600" />}
    >
      <Card className="bg-white border-gray-200 shadow-sm">
        <CardContent className="p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-semibold text-zinc-900">
              {pct}%
            </span>
            <span
              className={`text-xs font-medium text-white px-2 py-1 rounded-full ${bandColor(
                confidence
              )}`}
            >
              {bandLabel(confidence)}
            </span>
          </div>

          <div className="relative h-2 w-full rounded-full bg-gray-200 overflow-hidden">
            <div
              className={`h-full ${bandColor(confidence)}`}
              style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
            />
            <div
              className="absolute top-0 h-full w-px bg-gray-500/60"
              style={{ left: `${CLARIFY_THRESHOLD * 100}%` }}
            />
            <div
              className="absolute top-0 h-full w-px bg-gray-500/60"
              style={{ left: `${ANSWER_THRESHOLD * 100}%` }}
            />
          </div>

          <div className="grid grid-cols-2 gap-1 text-xs text-zinc-500">
            {Object.entries(breakdown).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span>{key.replace(/_/g, " ")}</span>
                <span className="text-zinc-900">{Math.round(value * 100)}%</span>
              </div>
            ))}
          </div>

          {nextStepHint && (
            <p className="text-xs text-zinc-600 pt-1 border-t border-gray-100">
              {nextStepHint}
            </p>
          )}
        </CardContent>
      </Card>
    </PanelSection>
  );
}
