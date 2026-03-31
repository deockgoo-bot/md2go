"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 p-8">
      <p className="text-4xl">⚠️</p>
      <h2 className="text-lg font-semibold text-gray-900">오류가 발생했습니다</h2>
      <p className="text-sm text-gray-500 text-center max-w-sm">{error.message}</p>
      <Button onClick={reset}>다시 시도</Button>
    </div>
  );
}
