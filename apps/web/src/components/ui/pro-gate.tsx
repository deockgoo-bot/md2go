"use client";

import { Lock, Bell } from "lucide-react";
import { useState } from "react";

interface ProGateProps {
  feature: string;
  children: React.ReactNode;
}

export function ProGate({ feature, children }: ProGateProps) {
  const [notified, setNotified] = useState(false);

  return (
    <div className="relative">
      {/* 흐린 UI */}
      <div className="pointer-events-none select-none opacity-30 blur-[2px]">
        {children}
      </div>

      {/* 오버레이 */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="bg-white/95 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-lg px-8 py-10 text-center max-w-sm">
          <div className="inline-flex p-3 bg-purple-100 rounded-full mb-4">
            <Lock className="h-6 w-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">{feature}</h3>
          <p className="text-sm text-gray-500 mb-6">
            Pro 플랜에서 사용 가능한 기능입니다.<br />
            곧 출시 예정입니다.
          </p>
          {notified ? (
            <div className="inline-flex items-center gap-2 text-sm text-green-600 font-medium">
              <Bell className="h-4 w-4" />
              알림 등록 완료
            </div>
          ) : (
            <button
              onClick={() => setNotified(true)}
              className="inline-flex items-center gap-2 bg-purple-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
            >
              <Bell className="h-4 w-4" />
              출시 알림 받기
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
