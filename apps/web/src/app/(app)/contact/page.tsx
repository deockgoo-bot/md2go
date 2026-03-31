"use client";

import { useState } from "react";
import { MessageCircle, Send, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", type: "general", message: "" });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  function set(k: keyof typeof form, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.email || !form.message) return;
    setLoading(true);
    setError("");

    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${BASE_URL}/api/v1/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("전송 실패");
      setSent(true);
    } catch {
      setError("전송에 실패했습니다. 이메일로 직접 문의해주세요.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <Card>
          <CardContent className="py-16 text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
            <h2 className="text-lg font-bold text-gray-900 mb-2">문의가 접수되었습니다</h2>
            <p className="text-sm text-gray-500">빠른 시일 내에 답변 드리겠습니다.</p>
            <button
              onClick={() => { setSent(false); setForm({ name: "", email: "", type: "general", message: "" }); }}
              className="mt-6 text-sm text-brand-600 hover:text-brand-700 font-medium"
            >
              추가 문의하기
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">문의하기</h1>
        <p className="text-sm text-gray-500 mt-0.5">기능 요청, 버그 신고, 제휴 문의 등</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4 text-brand-600" />
            문의 작성
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">이름</label>
                <input
                  value={form.name}
                  onChange={(e) => set("name", e.target.value)}
                  placeholder="홍길동"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">이메일 *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  placeholder="email@example.com"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">문의 유형</label>
              <div className="flex flex-wrap gap-2">
                {[
                  { value: "general", label: "일반 문의" },
                  { value: "bug", label: "버그 신고" },
                  { value: "feature", label: "기능 요청" },
                  { value: "partnership", label: "제휴/협업" },
                  { value: "pricing", label: "요금/Pro 플랜" },
                ].map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => set("type", t.value)}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      form.type === t.value
                        ? "bg-brand-600 text-white border-brand-600"
                        : "border-gray-200 text-gray-600 hover:border-brand-300"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">내용 *</label>
              <textarea
                value={form.message}
                onChange={(e) => set("message", e.target.value)}
                placeholder="문의 내용을 입력해주세요..."
                className="w-full h-36 text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
                required
              />
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              <Send className="h-4 w-4 mr-2" />
              문의 보내기
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
