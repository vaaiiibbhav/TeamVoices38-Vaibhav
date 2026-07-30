"use client";

import { ChevronRight, Route } from "lucide-react";
import { PanelSection } from "./panel-section";

interface PathBreadcrumbsProps {
  path: string[];
}

function formatNodeName(name: string) {
  return name.replace(/_/g, " ");
}

export function PathBreadcrumbs({ path }: PathBreadcrumbsProps) {
  return (
    <PanelSection
      title="Decision Path"
      icon={<Route className="h-4 w-4 text-blue-600" />}
    >
      <div className="flex flex-wrap items-center gap-1 text-xs">
        {path.map((node, i) => {
          const isLast = i === path.length - 1;
          return (
            <div key={`${node}-${i}`} className="flex items-center gap-1">
              <span
                className={`px-2 py-1 rounded-md border ${
                  isLast
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-zinc-700 border-gray-200"
                }`}
              >
                {formatNodeName(node)}
              </span>
              {!isLast && <ChevronRight className="h-3 w-3 text-zinc-400" />}
            </div>
          );
        })}
      </div>
    </PanelSection>
  );
}
