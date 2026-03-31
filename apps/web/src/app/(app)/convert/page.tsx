"use client";

import { useState } from "react";
import { Download, ArrowLeftRight } from "lucide-react";
import { FileUploader } from "@/components/upload/file-uploader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { convertHwpToMd, convertMdToHwp, getDownloadUrl } from "@/lib/api";

type Mode = "hwp-to-md" | "md-to-hwp";
type OutputFmt = "hwpx" | "hwp";

function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ConvertPage() {
  const [mode, setMode] = useState<Mode>("hwp-to-md");
  const [outputFmt, setOutputFmt] = useState<OutputFmt>("hwpx");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ job_id: string; markdown?: string } | null>(null);
  const [sourceFilename, setSourceFilename] = useState("");
  const [mdInput, setMdInput] = useState("");

  async function handleFile(file: File) {
    setError(""); setResult(null); setLoading(true);
    setSourceFilename(file.name.replace(/\.(hwp|hwpx)$/, ""));
    try {
      setResult(await convertHwpToMd(file));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "변환 실패");
    } finally {
      setLoading(false);
    }
  }

  async function handleMdConvert() {
    if (!mdInput.trim()) return;
    setError(""); setResult(null); setLoading(true);
    try {
      setResult(await convertMdToHwp(mdInput, outputFmt));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "변환 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">HWP 변환</h1>
        <p className="text-sm text-gray-500 mt-0.5">HWP ↔ MD 양방향 변환</p>
      </div>

      {/* 방향 토글 */}
      <div className="flex gap-2 p-1 bg-gray-100 rounded-lg w-fit">
        {(["hwp-to-md", "md-to-hwp"] as const).map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m); setResult(null); setError(""); }}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              mode === m ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {m === "hwp-to-md" ? "HWP → Markdown" : "Markdown → HWP"}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ArrowLeftRight className="h-4 w-4 text-brand-600" />
              {mode === "hwp-to-md" ? "HWP·HWPX 파일 업로드" : "Markdown 입력"}
            </CardTitle>
            {/* 출력 포맷 선택 */}
            {mode === "md-to-hwp" && (
              <div className="flex gap-1 p-0.5 bg-gray-100 rounded-md">
                {([
                  { value: "hwpx", label: ".hwpx", desc: "한글 2010+" },
                  { value: "hwp",  label: ".hwp",  desc: "한글 97+" },
                ] as const).map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setOutputFmt(f.value)}
                    title={f.desc}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      outputFmt === f.value ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === "hwp-to-md" ? (
            <FileUploader
              onFile={handleFile}
              loading={loading}
              accept=".hwp,.hwpx"
              hint=".hwp 또는 .hwpx 파일을 드래그하거나 클릭하세요 (최대 50MB)"
            />
          ) : (
            <div className="space-y-3">
              <textarea
                value={mdInput}
                onChange={(e) => setMdInput(e.target.value)}
                placeholder="# 제목&#10;&#10;본문 내용을 입력하세요..."
                className="w-full h-48 text-sm border border-gray-200 rounded-lg p-3 font-mono resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <Button onClick={handleMdConvert} loading={loading} disabled={!mdInput.trim()}>
                .{outputFmt} 로 변환
              </Button>
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 결과 */}
      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>변환 결과</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="success">완료</Badge>
                {mode === "hwp-to-md" && result.markdown && (
                  <button
                    onClick={() => downloadMarkdown(result.markdown!, `${sourceFilename || "converted"}.md`)}
                    className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium"
                  >
                    <Download className="h-4 w-4" /> .md 저장
                  </button>
                )}
                {mode === "md-to-hwp" && result.job_id && (
                  <a
                    href={getDownloadUrl(result.job_id, "convert", outputFmt)}
                    download
                    className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium"
                  >
                    <Download className="h-4 w-4" /> .{outputFmt} 저장
                  </a>
                )}
              </div>
            </div>
          </CardHeader>
          {result.markdown && (
            <CardContent>
              <pre className="text-xs bg-gray-50 rounded-lg p-4 overflow-auto max-h-80 whitespace-pre-wrap leading-relaxed font-mono">
                {result.markdown}
              </pre>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
