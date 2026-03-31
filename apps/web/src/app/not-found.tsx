import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 p-8">
      <p className="text-5xl font-bold text-gray-200">404</p>
      <h2 className="text-lg font-semibold text-gray-900">페이지를 찾을 수 없습니다</h2>
      <Link href="/" className="text-sm text-brand-600 hover:underline">
        홈으로 돌아가기
      </Link>
    </div>
  );
}
