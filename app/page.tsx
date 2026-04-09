"use client";

import { useCallback, useState } from "react";
import ProcessingStatus from "./components/ProcessingStatus";
import VideoResult from "./components/VideoResult";
import VideoUpload from "./components/VideoUpload";

const BACKEND_URL = "http://localhost:8000";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "ru", label: "Russian" },
  { code: "zh-cn", label: "Chinese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "hi", label: "Hindi" },
  { code: "ar", label: "Arabic" },
];

type AppPhase = "idle" | "processing" | "done" | "error";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("en");
  const [jobId, setJobId] = useState<string | null>(null);
  const [phase, setPhase] = useState<AppPhase>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!file || !text.trim()) return;

    const formData = new FormData();
    formData.append("video", file);
    formData.append("text", text.trim());
    formData.append("language", language);

    try {
      const res = await fetch(`${BACKEND_URL}/process`, {
        method: "POST",
        body: formData,
        // No Content-Type header — browser sets multipart boundary automatically
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: string }).error ?? `Server error ${res.status}`);
      }

      const data = (await res.json()) as { job_id: string };
      setJobId(data.job_id);
      setPhase("processing");
    } catch (e) {
      const msg =
        e instanceof Error
          ? e.message
          : "Failed to connect to backend. Is FastAPI running on port 8000?";
      setErrorMsg(msg);
      setPhase("error");
    }
  }, [file, text, language]);

  const handleReset = useCallback(() => {
    setFile(null);
    setText("");
    setJobId(null);
    setPhase("idle");
    setErrorMsg("");
  }, []);

  const canSubmit = file !== null && text.trim().length > 0;

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 flex flex-col items-center py-16 px-4">
      <div className="w-full max-w-2xl flex flex-col gap-8">

        {/* Header */}
        <header className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white">
            AI Video Dubbing
          </h1>
          <p className="mt-2 text-zinc-400 text-sm">
            Upload a video · Enter new script · Get lip-synced output
          </p>
        </header>

        {/* ── IDLE: input form ── */}
        {phase === "idle" && (
          <>
            <VideoUpload file={file} onFileChange={setFile} />

            <div className="flex flex-col gap-2">
              <label className="text-sm text-zinc-400 font-medium">
                New dialogue
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter the new script the speaker should say…"
                rows={5}
                className="w-full rounded-xl bg-zinc-800 border border-zinc-700 p-4
                           text-zinc-100 placeholder-zinc-500 resize-none
                           focus:outline-none focus:ring-2 focus:ring-violet-500
                           transition-shadow"
              />
            </div>

            <div className="flex items-center gap-4">
              <label className="text-sm text-zinc-400 font-medium shrink-0">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="flex-1 rounded-lg bg-zinc-800 border border-zinc-700
                           px-3 py-2 text-zinc-100
                           focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="w-full rounded-xl bg-violet-600 hover:bg-violet-500
                         disabled:bg-zinc-800 disabled:text-zinc-600
                         text-white font-semibold py-4 transition-colors
                         cursor-pointer disabled:cursor-not-allowed"
            >
              Start Dubbing
            </button>
          </>
        )}

        {/* ── PROCESSING ── */}
        {phase === "processing" && jobId && (
          <ProcessingStatus
            jobId={jobId}
            backendUrl={BACKEND_URL}
            onDone={() => setPhase("done")}
            onError={(msg) => {
              setErrorMsg(msg);
              setPhase("error");
            }}
          />
        )}

        {/* ── DONE ── */}
        {phase === "done" && jobId && (
          <VideoResult
            jobId={jobId}
            backendUrl={BACKEND_URL}
            onReset={handleReset}
          />
        )}

        {/* ── ERROR ── */}
        {phase === "error" && (
          <div className="rounded-xl bg-red-950 border border-red-800 p-6 text-center flex flex-col gap-4">
            <p className="text-red-300 text-sm leading-relaxed">{errorMsg}</p>
            <button
              onClick={handleReset}
              className="text-sm underline text-red-400 hover:text-red-300 transition-colors"
            >
              Try again
            </button>
          </div>
        )}

      </div>
    </main>
  );
}
