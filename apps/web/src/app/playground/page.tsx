"use client";

import { useState } from "react";
import { Download, Play, Copy, Check } from "lucide-react";

const EXAMPLES = {
  basic: `# 업무 보고서

일반 텍스트입니다.

두번째 문단.`,
  bold: `# 공문서 제목

일반 텍스트 **볼드 강조** 그리고 *이탤릭 참고*.

세 번째 문단입니다.`,
  table: `# 월간 보고

| 항목 | 상태 | 비고 |
|------|------|------|
| 변환 엔진 | 완료 | HWP + HWPX |
| AI 초안 | 완료 | Bedrock Claude |
| RAG 검색 | 진행중 | Pro 기능 |

이상입니다.`,
  mixed: `# 2026년 상반기 업무 계획

## 1. 배경

기존 HWP 문서 처리에 **많은 시간**이 소요됨.
*자동화 도구*가 필요한 상황임.

## 2. 목표

| 구분 | 목표 | 기한 |
|------|------|------|
| 변환 엔진 | 오류율 5% 이하 | 3월 |
| AI 초안 | 10종 템플릿 | 4월 |
| 배포 | 라이브 서비스 | 3월 |

## 3. 기대 효과

문서 작업 시간 단축 및 품질 향상.`,
};

const PIP_CODE = `# 설치
pip install hwp-converter-ai

# HWP 생성
from hwp_converter_ai import HwpWriter
HwpWriter().from_markdown(markdown, "output.hwp")

# HWPX 생성
from hwp_converter_ai import HwpxGenerator
HwpxGenerator().from_markdown(markdown, output_path="output.hwpx")

# HWP → Markdown
from hwp_converter_ai import HwpParser
ir = HwpParser.parse("input.hwp")
print(ir.to_markdown())`;

export default function PlaygroundPage() {
  const [markdown, setMarkdown] = useState(EXAMPLES.basic);
  const [format, setFormat] = useState<"hwp" | "hwpx">("hwp");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ job_id: string; download_url: string } | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleConvert() {
    if (!markdown.trim()) return;
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";
      const res = await fetch(`${BASE}/api/v1/convert/md-to-hwp`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": KEY },
        body: JSON.stringify({ markdown, format }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "변환 실패");
      }
      const data = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "변환 실패");
    } finally {
      setLoading(false);
    }
  }

  function copyCode() {
    navigator.clipboard.writeText(PIP_CODE);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="text-center mb-10">
          <h1 className="text-2xl font-bold text-gray-900">Playground</h1>
          <p className="text-gray-500 mt-1">Markdown을 입력하고 HWP/HWPX로 변환해보세요</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* 왼쪽: 입력 */}
          <div className="space-y-4">
            {/* 예제 선택 */}
            <div className="flex flex-wrap gap-2">
              {Object.entries(EXAMPLES).map(([key, _]) => (
                <button
                  key={key}
                  onClick={() => { setMarkdown(EXAMPLES[key as keyof typeof EXAMPLES]); setResult(null); }}
                  className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                    markdown === EXAMPLES[key as keyof typeof EXAMPLES]
                      ? "bg-brand-600 text-white border-brand-600"
                      : "border-gray-200 text-gray-600 hover:border-brand-300"
                  }`}
                >
                  {key === "basic" ? "기본" : key === "bold" ? "볼드/이탤릭" : key === "table" ? "표" : "혼합"}
                </button>
              ))}
            </div>

            {/* Markdown 입력 */}
            <textarea
              value={markdown}
              onChange={(e) => { setMarkdown(e.target.value); setResult(null); }}
              className="w-full h-80 text-sm font-mono border border-gray-200 rounded-xl p-4 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              placeholder="# 제목&#10;&#10;본문..."
            />

            {/* 변환 버튼 */}
            <div className="flex items-center gap-3">
              <div className="flex gap-1 p-0.5 bg-gray-100 rounded-md">
                {(["hwp", "hwpx"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                      format === f ? "bg-white shadow text-gray-900" : "text-gray-500"
                    }`}
                  >
                    .{f}
                  </button>
                ))}
              </div>
              <button
                onClick={handleConvert}
                disabled={loading || !markdown.trim()}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                변환하기
              </button>
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{error}</div>
            )}

            {result && (
              <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                <span className="text-sm text-green-700 font-medium">변환 완료!</span>
                <a
                  href={`${result.download_url}&api_key=${process.env.NEXT_PUBLIC_API_KEY ?? ""}`}
                  download
                  className="inline-flex items-center gap-1.5 text-sm text-green-700 hover:text-green-800 font-medium"
                >
                  <Download className="h-4 w-4" /> .{format} 다운로드
                </a>
              </div>
            )}
          </div>

          {/* 오른쪽: pip 코드 */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">Python 패키지로 동일한 작업</h3>
              <button
                onClick={copyCode}
                className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? "복사됨" : "복사"}
              </button>
            </div>
            <div className="bg-gray-900 rounded-xl p-5 overflow-auto h-80">
              <pre className="text-sm text-gray-300 leading-relaxed">
                <code>{PIP_CODE}</code>
              </pre>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
              <h4 className="text-sm font-semibold text-gray-700">설치</h4>
              <div className="bg-gray-50 rounded-lg px-4 py-2.5 font-mono text-sm text-gray-800">
                pip install hwp-converter-ai
              </div>
              <h4 className="text-sm font-semibold text-gray-700">지원 기능</h4>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                <span>✅ Markdown → HWP</span>
                <span>✅ Markdown → HWPX</span>
                <span>✅ HWP → Markdown</span>
                <span>✅ HWPX → Markdown</span>
                <span>✅ 볼드/이탤릭</span>
                <span>✅ 표 (테두리)</span>
                <span>✅ 이미지 추출</span>
                <span>✅ 긴 문서</span>
              </div>
              <a
                href="https://pypi.org/project/hwp-converter-ai/"
                target="_blank"
                className="block text-center text-sm text-brand-600 hover:text-brand-700 font-medium pt-2"
              >
                PyPI에서 보기 →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
