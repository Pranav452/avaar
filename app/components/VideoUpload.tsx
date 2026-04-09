"use client";

import { DragEvent, useRef, useState } from "react";

interface Props {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

export default function VideoUpload({ file, onFileChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "video/mp4") {
      onFileChange(dropped);
    }
  };

  const zoneClass = [
    "cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center",
    "transition-colors select-none",
    dragging
      ? "border-violet-400 bg-violet-950/40"
      : file
        ? "border-emerald-600 bg-emerald-950/20"
        : "border-zinc-700 bg-zinc-900 hover:border-zinc-500",
  ].join(" ");

  return (
    <div
      className={zoneClass}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4"
        className="hidden"
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
      />

      {file ? (
        <div className="flex flex-col items-center gap-1">
          <span className="text-emerald-400 font-medium">{file.name}</span>
          <span className="text-zinc-500 text-sm">
            {(file.size / 1024 / 1024).toFixed(1)} MB
          </span>
          <span className="text-zinc-600 text-xs mt-2">Click to change file</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-zinc-500">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-10 h-10 text-zinc-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          <p className="text-base">Drop MP4 here or click to browse</p>
          <p className="text-xs">Only .mp4 files accepted</p>
        </div>
      )}
    </div>
  );
}
