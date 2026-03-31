"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface FileUploaderProps {
  accept?: string;
  label?: string;
  hint?: string;
  onFile: (file: File) => void;
  loading?: boolean;
}

export function FileUploader({ accept = ".hwp,.hwpx", label = "HWP·HWPX 파일 업로드", hint, onFile, loading }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selected, setSelected] = useState<File | null>(null);

  function handleFile(file: File) {
    setSelected(file);
    onFile(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => !loading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
          dragging ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-brand-400 hover:bg-gray-50",
          loading && "pointer-events-none"
        )}
      >
        {loading ? (
          <>
            <div className="mx-auto h-10 w-10 border-4 border-gray-200 border-t-brand-600 rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium text-gray-700">AI 처리 중...</p>
            <p className="text-xs text-gray-400 mt-1">잠시만 기다려주세요</p>
          </>
        ) : (
          <>
            <Upload className="mx-auto h-10 w-10 text-gray-400 mb-3" />
            <p className="text-sm font-medium text-gray-700">{label}</p>
            <p className="text-xs text-gray-400 mt-1">{hint ?? `${accept} 파일을 드래그하거나 클릭하세요 (최대 50MB)`}</p>
          </>
        )}
        <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={onInputChange} />
      </div>

      {selected && (
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm">
          <FileText className="h-4 w-4 text-brand-600 shrink-0" />
          <span className="truncate text-gray-700 flex-1">{selected.name}</span>
          <span className="text-gray-400 shrink-0">{(selected.size / 1024).toFixed(0)} KB</span>
          <button
            onClick={(e) => { e.stopPropagation(); setSelected(null); }}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
