"use client";

import { useState } from "react";
import { Search, Upload } from "lucide-react";
import { FileUploader } from "@/components/upload/file-uploader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProGate } from "@/components/ui/pro-gate";
import { uploadAndIndex, searchDocuments, type SearchResult } from "@/lib/api";

function SearchPageContent() {
  const [indexLoading, setIndexLoading] = useState(false);
  const [indexed, setIndexed] = useState<{ filename: string; chunk_count: number }[]>([]);
  const [indexError, setIndexError] = useState("");

  const [query, setQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [searchError, setSearchError] = useState("");

  async function handleFile(file: File) {
    setIndexError(""); setIndexLoading(true);
    try {
      const res = await uploadAndIndex(file);
      setIndexed((prev) => [...prev, { filename: res.filename, chunk_count: res.chunk_count }]);
    } catch (e: unknown) {
      setIndexError(e instanceof Error ? e.message : "인덱싱 실패");
    } finally {
      setIndexLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearchError(""); setResults(null); setSearchLoading(true);
    try {
      const res = await searchDocuments(query);
      setResults(res.results);
      setElapsed(res.elapsed_ms);
    } catch (e: unknown) {
      setSearchError(e instanceof Error ? e.message : "검색 실패");
    } finally {
      setSearchLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-green-600" />
            문서 인덱싱
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FileUploader onFile={handleFile} loading={indexLoading} accept=".hwp,.hwpx" hint="HWP 또는 HWPX 파일을 업로드하면 자동으로 벡터 DB에 인덱싱됩니다" />
          {indexed.length > 0 && (
            <div className="space-y-1.5">
              {indexed.map((d, i) => (
                <div key={i} className="flex items-center justify-between text-sm px-3 py-2 bg-green-50 rounded-lg">
                  <span className="text-gray-700 truncate">{d.filename}</span>
                  <Badge variant="success">{d.chunk_count}개 청크</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-4 w-4 text-green-600" />
            자연어 검색
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="예: 예산 편성 절차는?"
              className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <Button type="submit" loading={searchLoading} disabled={!query.trim()}>
              검색
            </Button>
          </form>
        </CardContent>
      </Card>

      {results && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">{results.length}건 검색됨</p>
            <p className="text-xs text-gray-400">{elapsed.toFixed(0)}ms</p>
          </div>
          {results.map((r, i) => (
            <Card key={i}>
              <CardContent className="py-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500 truncate">{r.filename}</span>
                  <Badge variant="default">유사도 {(r.score * 100).toFixed(0)}%</Badge>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">{r.content}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">RAG 문서 검색</h1>
        <p className="text-sm text-gray-500 mt-0.5">HWP·HWPX 문서를 업로드하고 자연어로 검색</p>
      </div>
      <ProGate feature="RAG 문서 검색">
        <SearchPageContent />
      </ProGate>
    </div>
  );
}
