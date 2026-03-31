import Link from "next/link";
import { FileSymlink, PenLine, Search, CheckSquare, ArrowRight, Github, Zap, Shield, Globe } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-50 via-white to-purple-50" />
        <div className="relative max-w-5xl mx-auto px-6 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 bg-brand-100 text-brand-700 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
            <Zap className="h-3.5 w-3.5" />
            HWP 문서 자동화의 새로운 시작
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 leading-tight mb-5">
            HWP 문서를 AI로<br />
            <span className="text-brand-600">자동으로 생성하고 변환</span>하세요
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto mb-10">
            HWP 문서를 프로그래밍으로 자동 생성·변환·검색·교정.
            HWP 문서 작업에 들이는 시간을 줄일 수 있습니다.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/convert"
              className="inline-flex items-center gap-2 bg-brand-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-brand-700 transition-colors"
            >
              무료로 시작하기 <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/deockgoo-bot/md2go"
              className="inline-flex items-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-800 transition-colors"
            >
              <Github className="h-4 w-4" /> GitHub
            </a>
          </div>

          {/* 신뢰 지표 */}
          <div className="flex items-center justify-center gap-8 mt-12 text-sm text-gray-400">
            <span>HWP 5.0 호환</span>
            <span className="w-1 h-1 rounded-full bg-gray-300" />
            <span>공공기관 보안 준수</span>
            <span className="w-1 h-1 rounded-full bg-gray-300" />
            <span>오픈소스 엔진</span>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <h2 className="text-2xl font-bold text-gray-900">HWP 문서 작업, 이제 코드로</h2>
          <p className="text-gray-500 mt-2">복잡한 HWP 바이너리 포맷을 신경 쓸 필요 없습니다</p>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          {[
            {
              href: "/convert",
              icon: FileSymlink,
              color: "bg-blue-100 text-blue-600",
              title: "HWP 변환",
              desc: "HWP ↔ Markdown 양방향 변환. 표, 제목, 서식 보존.",
              tag: "오픈소스",
            },
            {
              href: "/draft",
              icon: PenLine,
              color: "bg-purple-100 text-purple-600",
              title: "AI 초안 생성",
              desc: "기안문·보고서·공고문 등 10종 공문서를 AI가 자동 작성.",
              tag: "Pro",
            },
            {
              href: "/search",
              icon: Search,
              color: "bg-green-100 text-green-600",
              title: "RAG 문서 검색",
              desc: "HWP 문서를 업로드하면 자연어로 내용을 검색.",
              tag: "Pro",
            },
            {
              href: "/correct",
              icon: CheckSquare,
              color: "bg-orange-100 text-orange-600",
              title: "요약·교정",
              desc: "맞춤법 + 행정 문체 교정. 교정 전·후 비교.",
              tag: "Pro",
            },
          ].map(({ href, icon: Icon, color, title, desc, tag }) => (
            <Link
              key={href}
              href={href}
              className="group bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg hover:border-brand-300 transition-all"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`inline-flex p-2.5 rounded-lg ${color}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  tag === "오픈소스" ? "bg-green-100 text-green-700" : "bg-purple-100 text-purple-700"
                }`}>
                  {tag}
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
              <p className="text-sm text-gray-500 mb-4">{desc}</p>
              <span className="inline-flex items-center gap-1 text-sm text-brand-600 font-medium group-hover:gap-2 transition-all">
                사용하기 <ArrowRight className="h-4 w-4" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* Why */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-2xl font-bold text-gray-900">왜 HWP Converter AI인가?</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              {
                icon: Zap,
                title: "간편한 자동화",
                desc: "Python 3줄이면 HWP 문서 생성. 별도 소프트웨어 설치 불필요.",
              },
              {
                icon: Shield,
                title: "공공기관 보안",
                desc: "파일 처리 후 즉시 삭제. 망분리 환경 온프레미스 배포 지원. Docker 한 줄로 설치.",
              },
              {
                icon: Globe,
                title: "오픈소스 엔진",
                desc: "변환 엔진 코어는 MIT 라이선스로 공개. 커뮤니티와 함께 성장.",
              },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="text-center">
                <div className="inline-flex p-3 bg-white rounded-xl shadow-sm mb-4">
                  <Icon className="h-6 w-6 text-brand-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900">3줄이면 HWP 생성</h2>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 max-w-2xl mx-auto">
          <div className="flex items-center gap-1.5 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <pre className="text-sm text-gray-300 leading-relaxed overflow-x-auto">
            <code>{`pip install hwp-converter-ai

from hwp_converter_ai import HwpWriter

HwpWriter().from_markdown("# 업무 보고\\n\\n내용입니다.", "report.hwp")`}</code>
          </pre>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-brand-600 py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">
            지금 시작하세요
          </h2>
          <p className="text-brand-100 mb-8">
            HWP 문서 자동화, 더 이상 어렵지 않습니다.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/convert"
              className="inline-flex items-center gap-2 bg-white text-brand-600 px-6 py-3 rounded-lg font-medium hover:bg-brand-50 transition-colors"
            >
              무료로 변환하기 <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-5xl mx-auto px-6 space-y-3">
          <div className="flex items-center justify-between text-sm text-gray-400">
            <span>HWP Converter AI</span>
            <div className="flex items-center gap-6">
              <a href="https://github.com/deockgoo-bot/md2go" className="hover:text-gray-600">GitHub</a>
              <a href="/privacy" className="hover:text-gray-600">개인정보처리방침</a>
              <a href="https://www.hancom.com/etc/hwpDownload.do" className="hover:text-gray-600">한컴 공식 스펙 기반</a>
            </div>
          </div>
          <p className="text-xs text-gray-300 text-center">HWP는 한글과컴퓨터의 등록 상표입니다. 본 서비스는 한컴과 무관한 독립 프로젝트입니다.</p>
        </div>
      </footer>
    </div>
  );
}
