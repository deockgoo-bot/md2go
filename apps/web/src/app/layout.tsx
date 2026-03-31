import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HWP Converter AI",
  description: "공공기관 HWPX 문서 자동화 플랫폼",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
