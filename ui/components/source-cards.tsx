"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";
import type { Source } from "@/lib/types";
import { PanelSection } from "./panel-section";

interface SourceCardsProps {
  sources: Source[];
}

export function SourceCards({ sources }: SourceCardsProps) {
  return (
    <PanelSection
      title="Sources"
      icon={<FileText className="h-4 w-4 text-blue-600" />}
    >
      {sources.length === 0 ? (
        <p className="text-xs text-zinc-500">No sources cited</p>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {sources.map((source, i) => (
            <Card
              key={`${source.doc_id}-${source.page}-${i}`}
              className="bg-white border-gray-200 shadow-sm"
            >
              <CardHeader className="p-3 pb-1">
                <CardTitle className="text-sm text-zinc-900">
                  {source.doc_title}
                  <span className="ml-2 text-xs font-normal text-zinc-500">
                    p.{source.page} &middot; {source.section}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-1">
                <p className="text-xs font-light text-zinc-500 line-clamp-3">
                  {source.snippet}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </PanelSection>
  );
}
