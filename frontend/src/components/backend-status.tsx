import { CheckCircle2, CircleAlert } from "lucide-react";

type ReadinessResponse = {
  status: "ready";
  database: "connected";
};

async function getBackendStatus(): Promise<"connected" | "unavailable"> {
  const baseUrl = process.env.FRONTEND_API_URL;
  if (!baseUrl) return "unavailable";

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) return "unavailable";
    const result = (await response.json()) as ReadinessResponse;
    return result.status === "ready" && result.database === "connected"
      ? "connected"
      : "unavailable";
  } catch {
    return "unavailable";
  }
}

export async function BackendStatus() {
  const status = await getBackendStatus();
  const connected = status === "connected";

  return (
    <div
      aria-label={`Backend ${status}`}
      className="inline-flex w-fit items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1.5"
    >
      {connected ? (
        <CheckCircle2 className="text-emerald-400" size={13} />
      ) : (
        <CircleAlert className="text-amber-400" size={13} />
      )}
      <span className="text-[11px] text-zinc-400">
        {connected ? "All systems ready" : "Backend unavailable"}
      </span>
    </div>
  );
}
