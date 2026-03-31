"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface DiffChange {
  type: string;
  before: string;
  after: string;
}

interface DiffViewerProps {
  original: string;
  corrected: string;
  changes: DiffChange[];
}

export function DiffViewer({ original, corrected, changes }: DiffViewerProps) {
  const [view, setView] = useState<"split" | "changes">("split");

  return (
    <div className="space-y-3">
      {/* 탭 */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["split", "changes"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              view === v
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {v === "split" ? "전·후 비교" : `변경 목록 (${changes.length}건)`}
          </button>
        ))}
      </div>

      {view === "split" ? (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1.5">교정 전</p>
            <pre className="text-xs bg-red-50 border border-red-100 rounded-lg p-3 whitespace-pre-wrap leading-relaxed overflow-auto max-h-96">
              {original}
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1.5">교정 후</p>
            <pre className="text-xs bg-green-50 border border-green-100 rounded-lg p-3 whitespace-pre-wrap leading-relaxed overflow-auto max-h-96">
              {corrected}
            </pre>
          </div>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-auto">
          {changes.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">변경 사항 없음</p>
          ) : (
            changes.map((c, i) => (
              <div key={i} className="flex gap-3 text-xs bg-gray-50 rounded-lg p-3">
                <span className={cn(
                  "shrink-0 px-1.5 py-0.5 rounded text-white font-medium",
                  c.type === "replace" ? "bg-yellow-500" : c.type === "delete" ? "bg-red-500" : "bg-green-500"
                )}>
                  {c.type === "replace" ? "수정" : c.type === "delete" ? "삭제" : "추가"}
                </span>
                <div className="flex-1 space-y-0.5">
                  {c.before && <p className="line-through text-red-600">{c.before}</p>}
                  {c.after  && <p className="text-green-700">{c.after}</p>}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
