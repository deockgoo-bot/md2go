"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileSymlink, PenLine, Search, CheckSquare, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/convert", icon: FileSymlink, label: "변환",    desc: "HWP ↔ Markdown" },
  { href: "/draft",   icon: PenLine,     label: "초안 생성", desc: "AI 공문서 작성" },
  { href: "/search",  icon: Search,      label: "검색",    desc: "RAG 문서 검색" },
  { href: "/correct", icon: CheckSquare, label: "교정",    desc: "맞춤법·문체" },
];

export function Sidebar() {
  const path = usePathname();

  return (
    <aside className="w-60 shrink-0 bg-gray-900 text-white flex flex-col min-h-screen">
      {/* 로고 */}
      <div className="px-5 py-5 border-b border-gray-700">
        <p className="text-base font-bold tracking-tight">HWP Converter AI</p>
        <p className="text-xs text-gray-400 mt-0.5">공공기관 문서 자동화</p>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, icon: Icon, label, desc }) => {
          const active = path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                active
                  ? "bg-brand-600 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium">{label}</p>
                <p className="text-xs opacity-60 truncate">{desc}</p>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* 문의 */}
      <div className="px-3 py-4 border-t border-gray-700">
        <Link
          href="/contact"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
            path === "/contact"
              ? "bg-brand-600 text-white"
              : "text-gray-400 hover:bg-gray-800 hover:text-white"
          )}
        >
          <MessageCircle className="h-4 w-4" />
          <span className="text-sm font-medium">문의</span>
        </Link>
      </div>
    </aside>
  );
}
