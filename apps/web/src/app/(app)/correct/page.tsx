"use client";

import { useState } from "react";
import { CheckSquare, Download, AlignLeft } from "lucide-react";
import { FileUploader } from "@/components/upload/file-uploader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DiffViewer } from "@/components/document/diff-viewer";
import { ProGate } from "@/components/ui/pro-gate";
import { proofreadFile, proofreadText, summarizeText, getDownloadUrl } from "@/lib/api";

function CorrectPageContent() {
  const [tab, setTab] = useState<"proofread" | "summarize">("proofread");
  const [proofMode, setProofMode] = useState<"file" | "text">("file");
  const [proofText, setProofText] = useState("");
  const [proofLoading, setProofLoading] = useState(false);
  const [proofError, setProofError] = useState("");
  const [proofResult, setProofResult] = useState<{ job_id: string; diff: { original: string; corrected: string; changes: { type: string; before: string; after: string }[] } } | null>(null);
  const [sumText, setSumText] = useState("");
  const [sumLoading, setSumLoading] = useState(false);
  const [sumError, setSumError] = useState("");
  const [summary, setSummary] = useState("");

  return (
    <div className="space-y-6">
      <div className="flex gap-1 p-1 bg-gray-100 rounded-lg w-fit">
        {(["proofread", "summarize"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              tab === t ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "proofread" ? "교정" : "요약"}
          </button>
        ))}
      </div>

      {tab === "proofread" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <CheckSquare className="h-4 w-4 text-orange-600" />
                교정 입력
              </CardTitle>
              <div className="flex gap-1 p-0.5 bg-gray-100 rounded-md">
                {(["file", "text"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setProofMode(m)}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      proofMode === m ? "bg-white shadow text-gray-900" : "text-gray-500"
                    }`}
                  >
                    {m === "file" ? "파일 업로드" : "텍스트 입력"}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {proofMode === "file" ? (
              <FileUploader onFile={() => {}} loading={proofLoading} accept=".hwp,.hwpx" hint=".hwp 또는 .hwpx 파일을 드래그하거나 클릭하세요" />
            ) : (
              <div className="space-y-3">
                <textarea
                  value={proofText}
                  onChange={(e) => setProofText(e.target.value)}
                  placeholder="교정할 공문서 텍스트를 입력하세요..."
                  className="w-full h-40 text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
                <Button loading={proofLoading} disabled={!proofText.trim()}>
                  교정하기
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "summarize" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlignLeft className="h-4 w-4 text-orange-600" />
              요약 입력
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              value={sumText}
              onChange={(e) => setSumText(e.target.value)}
              placeholder="요약할 공문서 텍스트를 입력하세요..."
              className="w-full h-48 text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
            <Button loading={sumLoading} disabled={!sumText.trim()} className="w-full">
              요약하기
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function CorrectPage() {
  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">요약·교정</h1>
        <p className="text-sm text-gray-500 mt-0.5">맞춤법·행정 문체 교정 및 문서 요약</p>
      </div>
      <ProGate feature="요약·교정">
        <CorrectPageContent />
      </ProGate>
    </div>
  );
}
