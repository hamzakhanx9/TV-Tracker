"use client";

import { AlertCircle, CheckCircle2, Film, LoaderCircle, Tv2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

type LibraryEntry = {
  media: {
    id: string;
    media_type: "MOVIE" | "TV";
    title: string;
    poster_path: string | null;
    genres: string[];
  };
  watch_status: "PLAN_TO_WATCH" | "WATCHING" | "COMPLETED" | "ON_HOLD" | "DROPPED";
  watched: boolean;
};

const statuses = [
  { value: "WATCHING", label: "Currently watching", color: "bg-violet-400" },
  { value: "PLAN_TO_WATCH", label: "Plan to watch", color: "bg-sky-400" },
  { value: "COMPLETED", label: "Completed", color: "bg-emerald-400" },
  { value: "ON_HOLD", label: "On hold", color: "bg-amber-400" },
  { value: "DROPPED", label: "Dropped", color: "bg-zinc-500" },
] as const;

export function StatisticsPanel() {
  const [library, setLibrary] = useState<LibraryEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completedDialogOpen, setCompletedDialogOpen] = useState(false);
  const [completedTab, setCompletedTab] = useState<"MOVIE" | "TV">("MOVIE");
  const completedDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadLibrary() {
      try {
        const response = await fetch("/api/v1/library", {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not load your stats.",
          );
        }
        if (!Array.isArray(body)) throw new Error("The library service returned invalid stats.");
        setLibrary(body as LibraryEntry[]);
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "Could not load your stats.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadLibrary();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const dialog = completedDialogRef.current;
    if (completedDialogOpen && dialog && !dialog.open) dialog.showModal();
    else if (!completedDialogOpen && dialog?.open) dialog.close();
  }, [completedDialogOpen]);

  if (loading) {
    return (
      <div className="panel flex min-h-48 items-center justify-center gap-3 text-sm text-zinc-400">
        <LoaderCircle className="animate-spin" size={17} />
        Loading your stats…
      </div>
    );
  }

  if (error) {
    return (
      <p className="flex items-center gap-2 text-sm text-red-300" role="alert">
        <AlertCircle size={16} />
        {error}
      </p>
    );
  }

  const entries = library ?? [];
  const movies = entries.filter((entry) => entry.media.media_type === "MOVIE").length;
  const shows = entries.filter((entry) => entry.media.media_type === "TV").length;
  const completedTitles = entries.filter((entry) => entry.watch_status === "COMPLETED");
  const completedMovies = completedTitles.filter((entry) => entry.media.media_type === "MOVIE");
  const completedShows = completedTitles.filter((entry) => entry.media.media_type === "TV");
  const visibleCompletedTitles = completedTab === "MOVIE" ? completedMovies : completedShows;
  const completed = completedTitles.length;
  const maxStatusCount = Math.max(
    1,
    ...statuses.map(({ value }) => entries.filter((entry) => entry.watch_status === value).length),
  );
  const genreCounts = new Map<string, number>();
  const watchingEntries = entries.filter(
    (entry) =>
      entry.watched ||
      entry.watch_status === "WATCHING" ||
      entry.watch_status === "COMPLETED",
  );
  for (const entry of watchingEntries) {
    for (const genre of new Set(entry.media.genres)) {
      genreCounts.set(genre, (genreCounts.get(genre) ?? 0) + 1);
    }
  }
  const rankedGenres = [...genreCounts].sort(
    ([genreA, countA], [genreB, countB]) => countB - countA || genreA.localeCompare(genreB),
  );
  const maxGenreCount = Math.max(1, ...rankedGenres.map(([, count]) => count));

  return (
    <section className="space-y-7">
      <header>
        <p className="eyebrow">YOUR LIBRARY AT A GLANCE</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Your stats</h1>
        <p className="mt-2 text-sm leading-6 text-zinc-400">
          A snapshot of the movies and shows you’re tracking.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Movies" value={movies} icon={<Film size={18} />} />
        <StatCard label="TV shows" value={shows} icon={<Tv2 size={18} />} />
        <button
          aria-haspopup="dialog"
          className="panel flex items-center justify-between p-5 text-left transition-colors hover:border-white/[0.12] focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-300"
          onClick={() => setCompletedDialogOpen(true)}
          type="button"
        >
          <span>
            <span className="block text-sm text-zinc-400">Completed titles</span>
            <span className="mt-2 block text-3xl font-semibold tracking-tight text-zinc-100">
              {completed}
            </span>
          </span>
          <span className="grid size-10 place-items-center rounded-xl bg-white/[0.04] text-zinc-400">
            <CheckCircle2 size={18} />
          </span>
        </button>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <section aria-labelledby="status-breakdown" className="panel space-y-5 p-5 sm:p-6">
          <div>
            <h2 className="text-sm font-medium text-white" id="status-breakdown">
              Library breakdown
            </h2>
            <p className="mt-1 text-xs text-zinc-500">{entries.length} tracked titles</p>
          </div>
          {entries.length === 0 ? (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.025] px-4 py-6 text-center">
              <p className="text-sm text-zinc-400">
                Add a movie or show to start building your stats.
              </p>
              <Link className="subtle-link mt-3 inline-flex" href="/discover">
                Explore titles
              </Link>
            </div>
          ) : (
            <ul className="space-y-4">
              {statuses.map(({ value, label, color }) => {
                const count = entries.filter((entry) => entry.watch_status === value).length;
                const width = `${(count / maxStatusCount) * 100}%`;
                return (
                  <li className="space-y-2" key={value}>
                    <div className="flex items-center justify-between gap-4 text-xs">
                      <span className="text-zinc-300">{label}</span>
                      <span className="tabular-nums text-zinc-500">{count}</span>
                    </div>
                    <div
                      aria-label={`${label}: ${count}`}
                      className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]"
                      role="img"
                    >
                      <div className={`h-full rounded-full ${color}`} style={{ width }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section aria-labelledby="genre-breakdown" className="panel space-y-5 p-5 sm:p-6">
          <div>
            <h2 className="text-sm font-medium text-white" id="genre-breakdown">
              Genres you watch
            </h2>
            <p className="mt-1 text-xs text-zinc-500">
              Genres across titles you’ve watched or are watching
            </p>
          </div>
          {rankedGenres.length === 0 ? (
            <p className="rounded-xl border border-white/[0.06] bg-white/[0.025] px-4 py-6 text-center text-sm text-zinc-400">
              Genre breakdowns will appear as you add titles with genre details.
            </p>
          ) : (
            <ul className="space-y-4">
              {rankedGenres.map(([genre, count]) => (
                <li className="space-y-2" key={genre}>
                  <div className="flex items-center justify-between gap-4 text-xs">
                    <span className="text-zinc-300">{genre}</span>
                    <span className="tabular-nums text-zinc-500">
                      {count} {count === 1 ? "title" : "titles"}
                    </span>
                  </div>
                  <div
                    aria-label={`${genre}: ${count} ${count === 1 ? "title" : "titles"}`}
                    className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]"
                    role="img"
                  >
                    <div
                      className="h-full rounded-full bg-violet-400"
                      style={{ width: `${(count / maxGenreCount) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <dialog
        aria-labelledby="completed-titles-heading"
        className="fixed inset-0 m-0 h-dvh max-h-dvh w-screen max-w-none border-0 bg-transparent p-0 text-zinc-100 backdrop:bg-black/80 open:flex open:items-center open:justify-center"
        onClick={(event) => {
          if (event.target === event.currentTarget) setCompletedDialogOpen(false);
        }}
        onClose={() => setCompletedDialogOpen(false)}
        ref={completedDialogRef}
      >
        <section className="panel m-4 flex max-h-[min(760px,calc(100dvh-2rem))] w-full max-w-2xl flex-col overflow-hidden shadow-2xl shadow-black/50">
          <header className="flex items-start justify-between gap-4 border-b border-white/[0.07] p-5 sm:p-6">
            <div>
              <p className="eyebrow">YOUR FINISHED TITLES</p>
              <h2
                className="mt-2 text-xl font-semibold tracking-tight text-zinc-100"
                id="completed-titles-heading"
              >
                Completed titles
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                {completed} {completed === 1 ? "movie or show" : "movies and shows"}
              </p>
            </div>
            <button
              aria-label="Close completed titles"
              className="grid size-9 shrink-0 place-items-center rounded-lg border border-white/[0.07] text-zinc-400 transition-colors hover:bg-white/[0.05] hover:text-zinc-100"
              onClick={() => setCompletedDialogOpen(false)}
              type="button"
            >
              <X size={17} />
            </button>
          </header>
          <div className="overflow-y-auto p-4 sm:p-6">
            <div
              aria-label="Completed title type"
              className="mb-4 grid grid-cols-2 gap-1 rounded-xl border border-white/[0.06] bg-white/[0.025] p-1"
              role="group"
            >
              <button
                aria-pressed={completedTab === "MOVIE"}
                className={`rounded-lg px-3 py-2 text-sm transition-colors ${
                  completedTab === "MOVIE"
                    ? "bg-violet-400/[0.13] font-medium text-violet-200"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
                onClick={() => setCompletedTab("MOVIE")}
                type="button"
              >
                Movies <span className="ml-1 text-xs opacity-70">{completedMovies.length}</span>
              </button>
              <button
                aria-pressed={completedTab === "TV"}
                className={`rounded-lg px-3 py-2 text-sm transition-colors ${
                  completedTab === "TV"
                    ? "bg-violet-400/[0.13] font-medium text-violet-200"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
                onClick={() => setCompletedTab("TV")}
                type="button"
              >
                Shows <span className="ml-1 text-xs opacity-70">{completedShows.length}</span>
              </button>
            </div>
            {visibleCompletedTitles.length === 0 ? (
              <p className="rounded-xl border border-white/[0.06] bg-white/[0.025] px-4 py-8 text-center text-sm text-zinc-400">
                No completed {completedTab === "MOVIE" ? "movies" : "shows"} yet.
              </p>
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2">
                {visibleCompletedTitles.map(({ media }) => (
                  <li key={media.id}>
                    <Link
                      className="flex min-w-0 items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5 transition-colors hover:bg-white/[0.05]"
                      href={`/media/${media.id}`}
                      onClick={() => setCompletedDialogOpen(false)}
                    >
                      <span
                        aria-label={`${media.title} poster`}
                        className="grid size-14 shrink-0 place-items-center overflow-hidden rounded-lg bg-white/[0.04] text-zinc-500"
                        role="img"
                        style={
                          media.poster_path
                            ? {
                                backgroundImage: `url("${media.poster_path}")`,
                                backgroundSize: "cover",
                                backgroundPosition: "center",
                              }
                            : undefined
                        }
                      >
                        {!media.poster_path &&
                          (media.media_type === "MOVIE" ? <Film size={18} /> : <Tv2 size={18} />)}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-zinc-200">
                          {media.title}
                        </span>
                        <span className="mt-1 block text-xs text-zinc-500">
                          {media.media_type === "MOVIE" ? "Movie" : "TV show"}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </dialog>
    </section>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: ReactNode;
}) {
  return (
    <article className="panel flex items-center justify-between p-5">
      <div>
        <p className="text-sm text-zinc-400">{label}</p>
        <p className="mt-2 text-3xl font-semibold tracking-tight text-zinc-100">{value}</p>
      </div>
      <span className="grid size-10 place-items-center rounded-xl bg-white/[0.04] text-zinc-400">
        {icon}
      </span>
    </article>
  );
}
