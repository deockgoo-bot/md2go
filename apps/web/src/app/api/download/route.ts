import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export async function GET(req: NextRequest) {
  const jobId = req.nextUrl.searchParams.get("jobId");
  const fmt = req.nextUrl.searchParams.get("fmt") ?? "hwp";
  const type = req.nextUrl.searchParams.get("type") ?? "convert";

  if (!jobId) {
    return new Response("jobId required", { status: 400 });
  }

  const paths: Record<string, string> = {
    convert: `/api/v1/convert/download/${jobId}?fmt=${fmt}`,
    draft: `/api/v1/draft/download/${jobId}?fmt=${fmt}`,
    correct: `/api/v1/correct/download/${jobId}`,
  };

  const sep = paths[type].includes("?") ? "&" : "?";
  const res = await fetch(`${API_URL}${paths[type]}${sep}api_key=${API_KEY}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status });
  }

  const buffer = await res.arrayBuffer();

  // 디버그: 프록시가 전달하는 파일을 /tmp에 저장
  const fs = await import("fs");
  fs.writeFileSync(`/tmp/proxy_debug_${jobId}.hwp`, Buffer.from(buffer));
  console.log(`[proxy] jobId=${jobId} size=${buffer.byteLength}`);

  return new Response(buffer, {
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="converted.${fmt}"`,
      "Content-Length": String(buffer.byteLength),
    },
  });
}
