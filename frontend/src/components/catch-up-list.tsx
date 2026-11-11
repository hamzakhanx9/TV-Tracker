"use client";

import { AlertCircle, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type CatchUpShow = {
  media_id: string;
  title: string;
  unwatched_count: number;
};

export function CatchUpList() {
  const [shows, setShows] = useState<CatchUpShow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(
          `/api/v1/catch-up?${new URLSearchParams({ timezone })}`,
          { cache: "no-store", signal: controller.signal },
        );
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not load catch-up progress.",
          );
        }
        setShows(body as CatchUpShow[]);
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "Could not load catch-up progress.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  return (
    <section className="space-y-5">
      <header>
        <p className="eyebrow">YOUR CURRENTLY WATCHING LIST</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Catch Up</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Aired episodes in shows you are watching that are not marked watched.
        </p>
      </header>
      {error && (
        <p className="flex items-center gap-2 text-sm text-red-300" role="alert">
          <AlertCircle size={16} />
          {error}
        </p>
      )}
      {loading ? (
        <div className="panel flex min-h-40 items-center justify-center gap-3 text-sm text-zinc-400">
          <LoaderCircle className="animate-spin" size={17} />
          Finding episodes to catch up on…
        </div>
      ) : shows.length === 0 ? (
        <div className="panel p-8 text-center">
          <h2 className="font-medium text-white">You’re all caught up</h2>
          <p className="mt-2 text-sm text-zinc-500">
            Aired unwatched episodes from your currently watching shows will appear here.
          </p>
          <Link className="subtle-link mt-4 inline-flex" href="/tv">
            Browse TV shows
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {shows.map((show) => (
            <article className="panel p-5" key={show.media_id}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <Link
                  className="text-base font-medium text-white hover:text-violet-200"
                  href={`/media/${show.media_id}`}
                >
                  {show.title}
                </Link>
                <span className="text-xs text-zinc-500">
                  {show.unwatched_count}{" "}
                  {show.unwatched_count === 1 ? "episode" : "episodes"} to catch up on
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
