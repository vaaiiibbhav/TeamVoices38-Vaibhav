"use client";

import { Bot } from "lucide-react";
import type {
  Agent,
  AgentEvent,
  GuardrailCheck,
  InspectorPayload,
} from "@/lib/types";
import { Guardrails } from "./guardrails";
import { ConversationContext } from "./conversation-context";
import { ConfidenceGauge } from "./confidence-gauge";
import { SourceCards } from "./source-cards";
import { PathBreadcrumbs } from "./path-breadcrumbs";

const EMPTY_INSPECTOR: InspectorPayload = {
  trace_id: "",
  confidence: 0,
  breakdown: {},
  reason_codes: [],
  next_step_hint: "",
  route: "",
  path: [],
  intent: null,
  slots: {},
  sources: [],
  latency_ms: 0,
  pending_approval: false,
};

interface AgentPanelProps {
  // Accepted for backward compatibility with page.tsx's current
  // (unmodified ChatKit-era) call site — unused here now that Inspector
  // data drives this panel. Drop these once page.tsx is reworked to fetch
  // and pass real inspector data (a separate, bigger task).
  agents?: Agent[];
  currentAgent?: string;
  events?: AgentEvent[];
  guardrails?: GuardrailCheck[];
  context: Record<string, any>;
  inspector?: InspectorPayload;
}

export function AgentPanel({
  context,
  inspector = EMPTY_INSPECTOR,
}: AgentPanelProps) {
  return (
    <div className="w-3/5 h-full flex flex-col border-r border-gray-200 bg-white rounded-xl shadow-sm">
      <div className="bg-blue-600 text-white h-12 px-4 flex items-center gap-3 shadow-sm rounded-t-xl">
        <Bot className="h-5 w-5" />
        <h1 className="font-semibold text-sm sm:text-base lg:text-lg">
          Agent View
        </h1>
        <span className="ml-auto text-xs font-light tracking-wide opacity-80">
          Airline&nbsp;Co.
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
        <ConfidenceGauge
          confidence={inspector.confidence}
          breakdown={inspector.breakdown}
          nextStepHint={inspector.next_step_hint}
        />
        <SourceCards sources={inspector.sources} />
        <PathBreadcrumbs path={inspector.path} />
        <ConversationContext context={context} />
        <Guardrails reasonCodes={inspector.reason_codes} />
      </div>
    </div>
  );
}
