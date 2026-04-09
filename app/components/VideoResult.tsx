"use client";

interface Props {
  jobId: string;
  backendUrl: string;
  onReset: () => void;
}

export default function VideoResult({ jobId, backendUrl, onReset }: Props) {
  const downloadUrl = `${backendUrl}/download/${jobId}`;

  return (
    <div className="rounded-2xl bg-zinc-900 border border-zinc-800 p-6 flex flex-col gap-5">
      <h2 className="text-lg font-semibold text-emerald-400 text-center">
        Dubbing complete
      </h2>

      {/* Video player — streams directly from FastAPI (supports range requests) */}
      <video
        controls
        className="w-full rounded-xl bg-black"
        src={downloadUrl}
      />

      <div className="flex gap-3">
        <a
          href={downloadUrl}
          download={`dubbed_${jobId.slice(0, 8)}.mp4`}
          className="flex-1 text-center rounded-xl bg-violet-600 hover:bg-violet-500
                     text-white font-semibold py-3 transition-colors"
        >
          Download MP4
        </a>
        <button
          onClick={onReset}
          className="flex-1 rounded-xl border border-zinc-700 hover:border-zinc-500
                     text-zinc-300 hover:text-zinc-100 font-semibold py-3 transition-colors"
        >
          Dub another
        </button>
      </div>
    </div>
  );
}
