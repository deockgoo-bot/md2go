"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="ko">
      <body className="flex flex-col items-center justify-center min-h-screen gap-4 bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-900">심각한 오류가 발생했습니다</h2>
        <button
          onClick={reset}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          새로고침
        </button>
      </body>
    </html>
  );
}
