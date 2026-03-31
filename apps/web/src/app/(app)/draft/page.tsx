"use client";

import { useState } from "react";
import { PenLine, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { generateDraft, getDownloadUrl } from "@/lib/api";

const TEMPLATES = [
  "기안문", "보고서", "공고문", "지시문", "회의록",
  "업무협조전", "계획서", "결과보고서", "공문", "통보문",
];

type OutputFmt = "hwpx" | "hwp";

export default function DraftPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ job_id: string; markdown?: string } | null>(null);
  const [outputFmt, setOutputFmt] = useState<OutputFmt>("hwpx");

  const [form, setForm] = useState({
    template: "기안문",
    title: "",
    body_hint: "",
    department: "",
    reference_number: "",
  });

  function set(k: keyof typeof form, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title || !form.body_hint) return;
    setError(""); setResult(null); setLoading(true);
    try {
      const res = await generateDraft({ ...form, format: outputFmt });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "생성 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">AI 초안 생성</h1>
        <p className="text-sm text-gray-500 mt-0.5">행정안전부 공문서 규정 준수 초안 자동 작성</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PenLine className="h-4 w-4 text-purple-600" />
            초안 정보 입력
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 문서 종류 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">문서 종류</label>
              <div className="flex flex-wrap gap-2">
                {TEMPLATES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => set("template", t)}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      form.template === t
                        ? "bg-purple-600 text-white border-purple-600"
                        : "border-gray-200 text-gray-600 hover:border-purple-300"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* 제목 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">제목 *</label>
              <input
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder="예: 2026년 상반기 업무계획 수립 알림"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>

            {/* 본문 힌트 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">본문 내용 힌트 *</label>
              <textarea
                value={form.body_hint}
                onChange={(e) => set("body_hint", e.target.value)}
                placeholder="예: 2026년 상반기 부서별 업무계획을 3월 15일까지 제출 요청. 계획서 양식은 첨부 파일 참고."
                className="w-full h-28 text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">기안 부서</label>
                <input
                  value={form.department}
                  onChange={(e) => set("department", e.target.value)}
                  placeholder="예: 기획재정과"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">문서번호</label>
                <input
                  value={form.reference_number}
                  onChange={(e) => set("reference_number", e.target.value)}
                  placeholder="예: 기획-2026-001"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>

            {/* 출력 포맷 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">출력 형식</label>
              <div className="flex gap-1 p-0.5 bg-gray-100 rounded-md w-fit">
                {([
                  { value: "hwpx", label: ".hwpx", desc: "한글 2010+" },
                  { value: "hwp",  label: ".hwp",  desc: "한글 97+" },
                ] as const).map((f) => (
                  <button
                    key={f.value}
                    type="button"
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
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              초안 생성 (최대 60초)
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>생성된 초안</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="success">완료</Badge>
                {result.job_id && (
                  <a
                    href={getDownloadUrl(result.job_id, "draft", outputFmt)}
                    download
                    className="inline-flex items-center gap-1.5 text-sm text-purple-600 hover:text-purple-700 font-medium"
                  >
                    <Download className="h-4 w-4" /> .{outputFmt} 다운로드
                  </a>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-gray-50 rounded-lg p-4 overflow-auto max-h-96 whitespace-pre-wrap leading-relaxed">
              {result.markdown}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
