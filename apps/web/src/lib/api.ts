const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEFAULT_API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function getApiKey(): string {
  if (typeof window === "undefined") return DEFAULT_API_KEY;
  return localStorage.getItem("hwpconverter_api_key") || DEFAULT_API_KEY;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiKey = getApiKey();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "X-API-Key": apiKey,
      ...init.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "요청 실패");
  }
  return res.json() as Promise<T>;
}

// ────────────────────────────────────────────────────────────
// Convert
// ────────────────────────────────────────────────────────────

export interface ConvertResponse {
  job_id: string;
  status: string;
  markdown?: string;
  download_url?: string;
}

export async function convertHwpToMd(file: File): Promise<ConvertResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<ConvertResponse>("/api/v1/convert/hwp-to-md", {
    method: "POST",
    body: form,
  });
}

export async function convertMdToHwp(
  markdown: string,
  format: "hwp" | "hwpx" | "hwp-legacy" = "hwpx",
  template = "default",
): Promise<ConvertResponse> {
  return request<ConvertResponse>("/api/v1/convert/md-to-hwp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown, format, template }),
  });
}

export function getDownloadUrl(
  jobId: string,
  type: "convert" | "draft" | "correct",
  fmt: "hwp" | "hwpx" = "hwpx",
): string {
  const apiKey = getApiKey();
  const paths: Record<string, string> = {
    convert: `/api/v1/convert/download/${jobId}?fmt=${fmt}&api_key=${apiKey}`,
    draft:   `/api/v1/draft/download/${jobId}?fmt=${fmt}&api_key=${apiKey}`,
    correct: `/api/v1/correct/download/${jobId}?api_key=${apiKey}`,
  };
  return `${BASE_URL}${paths[type]}`;
}

// ────────────────────────────────────────────────────────────
// Draft
// ────────────────────────────────────────────────────────────

export interface DraftRequest {
  template: string;
  title: string;
  body_hint: string;
  department?: string;
  reference_number?: string;
  format?: "hwpx" | "hwp" | "hwp-legacy";
}

export interface DraftResponse {
  job_id: string;
  status: string;
  markdown?: string;
  download_url?: string;
}

export async function generateDraft(body: DraftRequest): Promise<DraftResponse> {
  return request<DraftResponse>("/api/v1/draft/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ────────────────────────────────────────────────────────────
// Search
// ────────────────────────────────────────────────────────────

export interface UploadIndexResponse {
  document_id: string;
  filename: string;
  status: string;
  chunk_count: number;
}

export async function uploadAndIndex(file: File): Promise<UploadIndexResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadIndexResponse>("/api/v1/search/upload", {
    method: "POST",
    body: form,
  });
}

export interface SearchResult {
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  content: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  elapsed_ms: number;
}

export async function searchDocuments(query: string, topK = 5): Promise<SearchResponse> {
  return request<SearchResponse>("/api/v1/search/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
}

// ────────────────────────────────────────────────────────────
// Correct
// ────────────────────────────────────────────────────────────

export interface SummarizeResponse {
  job_id: string;
  summary: string;
}

export async function summarizeText(text: string): Promise<SummarizeResponse> {
  return request<SummarizeResponse>("/api/v1/correct/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export interface ProofreadDiff {
  original: string;
  corrected: string;
  changes: { type: string; before: string; after: string }[];
}

export interface ProofreadResponse {
  job_id: string;
  diff: ProofreadDiff;
  download_url?: string;
}

export async function proofreadFile(file: File): Promise<ProofreadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<ProofreadResponse>("/api/v1/correct/proofread-file", {
    method: "POST",
    body: form,
  });
}

export async function proofreadText(text: string): Promise<ProofreadResponse> {
  return request<ProofreadResponse>("/api/v1/correct/proofread", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}
