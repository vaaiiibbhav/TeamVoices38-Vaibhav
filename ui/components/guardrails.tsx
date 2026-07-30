"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, TriangleAlert, CircleDot } from "lucide-react";
import { PanelSection } from "./panel-section";

interface GuardrailsProps {
  reasonCodes: string[];
}

const REASON_CODES = [
  "NO_POLICY_MATCH",
  "MISSING_SLOT",
  "ANSWER_NOT_ENTAILED",
  "CONFLICTING_SOURCES",
  "STALE_DOCUMENT",
  "OUT_OF_SCOPE",
] as const;

const REASON_LABELS: Record<string, string> = {
  NO_POLICY_MATCH: "No Policy Match",
  MISSING_SLOT: "Missing Slot",
  ANSWER_NOT_ENTAILED: "Answer Not Entailed",
  CONFLICTING_SOURCES: "Conflicting Sources",
  STALE_DOCUMENT: "Stale Document",
  OUT_OF_SCOPE: "Out Of Scope",
};

const REASON_DESCRIPTIONS: Record<string, string> = {
  NO_POLICY_MATCH: "No matching policy was found in the indexed documents.",
  MISSING_SLOT: "Required information is missing from the question.",
  ANSWER_NOT_ENTAILED:
    "The drafted answer wasn't well supported by the retrieved text.",
  CONFLICTING_SOURCES: "Retrieved sources appear to disagree with each other.",
  STALE_DOCUMENT: "The best-matching document may be out of date.",
  OUT_OF_SCOPE: "This question falls outside CampusFlow's supported topics.",
};

export function Guardrails({ reasonCodes }: GuardrailsProps) {
  return (
    <PanelSection
      title="Reason Codes"
      icon={<Shield className="h-4 w-4 text-blue-600" />}
    >
      <div className="grid grid-cols-3 gap-3">
        {REASON_CODES.map((code) => {
          const fired = reasonCodes.includes(code);
          return (
            <Card
              key={code}
              className={`bg-white border-gray-200 transition-all ${
                fired ? "" : "opacity-60"
              }`}
            >
              <CardHeader className="p-3 pb-1">
                <CardTitle className="text-sm flex items-center text-zinc-900">
                  {REASON_LABELS[code]}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-1">
                <p className="text-xs font-light text-zinc-500 mb-1">
                  {REASON_DESCRIPTIONS[code]}
                </p>
                <div className="flex text-xs">
                  {fired ? (
                    <Badge className="mt-2 px-2 py-1 bg-amber-500 hover:bg-amber-600 flex items-center text-white">
                      <TriangleAlert className="h-4 w-4 mr-1 text-white" />
                      Flagged
                    </Badge>
                  ) : (
                    <Badge className="mt-2 px-2 py-1 bg-gray-200 hover:bg-gray-300 flex items-center text-gray-600">
                      <CircleDot className="h-4 w-4 mr-1 text-gray-600" />
                      Clear
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </PanelSection>
  );
}
