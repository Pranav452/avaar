"use client";

import { useEffect, useState } from "react";

interface StatusData {
  status: "queued" | "processing" | "done" | "error" | "not_found";
  progress: number;
  message: string;
}

interface Props {
  jobId: string;
  backendUrl: string;
  onDone: () => void;
  onError: (msg: string) => void;
}

const STEPS = [
  { threshold: 5, label: "Extracting audio from video" },
  { threshold: 20, label: "Cloning voice with XTTS-v2" },
  { threshold: 60, label: "Syncing lips with Wav2Lip" },
  { threshold: 100, label: "Finalising output" },
];

export default function ProcessingStatus({
  jobId,
  backendUrl,
  onDone,
  onError,
}: Props) {
  const [data, setData] = useState<StatusData>({
    status: "queued",
    progress: 0,
    message: "Waiting to start…",
  });

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const res = await fetch(`${backendUrl}/status/${jobId}`);
        if (!res.ok) return; // keep polling on transient network errors
        const json = (await res.json()) as StatusData;
        if (!active) return;

        setData(json);

        if (json.status === "done") {
          clearInterval(timer);
          onDone();
        } else if (json.status === "error") {
          clearInterval(timer);
          onError(json.message);
        }
      } catch {
        // network hiccup — keep polling
      }
    };

    poll(); // immediate first check
    const timer = setInterval(poll, 2000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [jobId, backendUrl, onDone, onError]);

  return (
    <div className="rounded-2xl bg-zinc-900 border border-zinc-800 p-8 flex flex-col gap-6">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-sm text-zinc-400 mb-2">
          <span className="truncate pr-4">{data.message}</span>
          <span className="shrink-0">{data.progress}%</span>
        </div>
        <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
          <div
            className="bg-violet-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${data.progress}%` }}
          />
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex flex-col gap-3">
        {STEPS.map((step) => {
          const done = data.progress >= step.threshold;
          const active =
            data.progress < step.threshold &&
            data.progress >= (STEPS[STEPS.indexOf(step) - 1]?.threshold ?? 0);
          return (
            <div key={step.label} className="flex items-center gap-3 text-sm">
              <div
                className={[
                  "w-2.5 h-2.5 rounded-full shrink-0 transition-colors",
                  done
                    ? "bg-violet-400"
                    : active
                      ? "bg-violet-700 animate-pulse"
                      : "bg-zinc-700",
                ].join(" ")}
              />
              <span
                className={
                  done ? "text-zinc-200" : active ? "text-zinc-400" : "text-zinc-600"
                }
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-zinc-600 text-center leading-relaxed">
        First run downloads XTTS-v2 (~1.8 GB). Subsequent runs are faster.
      </p>
    </div>
  );
}
