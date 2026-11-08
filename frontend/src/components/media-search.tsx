"use client";

import { ArrowDownToLine, ChevronDown, Film, LoaderCircle, Search, Tv2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { MediaRatings, RatingBadge, type Ratings } from "@/components/media-ratings";

type MediaResult = {
  provider: "tmdb";
  external_id: string;
  media_type: "MOVIE" | "TV";
  title: string;
  overview: string | null;
  release_date: string | null;
  first_air_date: string | null;
  poster_path: string | null;
  tmdb_rating: number | null;
  tmdb_vote_count: number | null;
};

type MediaKind = "ALL" | "MOVIE" | "TV";

export function MediaSearch() {
  const [query, setQuery] = useState("");
  const [mediaKind, setMediaKind] = useState<MediaKind>("ALL");
  const [results, setResults] = useState<MediaResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [importing, setImporting] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [ratingsByKey, setRatingsByKey] = useState<Record<string, Ratings>>({});
  const [ratingsLoading, setRatingsLoading] = useState<string | null>(null);
  const [ratingsError, setRatingsError] = useState<string | null>(null);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setError("Enter at least two characters to search.");
      return;
    }

    setLoading(true);
    setError("");
    setNotice("");
    setAdded(new Set());
    try {
      const params = new URLSearchParams({ q: trimmed });
      if (mediaKind !== "ALL") params.set("media_type", mediaKind);
      const response = await fetch(`/api/v1/media/search?${params}`);
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(readError(body?.detail));
      if (!Array.isArray(body)) throw new Error("The search service returned an invalid response.");
      setResults(body as MediaResult[]);
      setExpandedKey(null);
      setRatingsByKey({});
      if ((body as MediaResult[]).length === 0) setNotice("No matching titles found.");
    } catch (requestError) {
      setResults([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Search is unavailable right now. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function toggleDetails(item: MediaResult, key: string) {
    if (expandedKey === key) {
      setExpandedKey(null);
      return;
    }
    setExpandedKey(key);
    setRatingsError(null);
    if (ratingsByKey[key]) return;

    setRatingsLoading(key);
    try {
      const response = await fetch(
        `/api/v1/media/${item.media_type}/${item.external_id}/ratings`,
      );
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(readError(body?.detail));
      setRatingsByKey((current) => ({ ...current, [key]: body as Ratings }));
    } catch (requestError) {
      setRatingsError(
        requestError instanceof Error ? requestError.message : "Could not load title ratings.",
      );
    } finally {
      setRatingsLoading(null);
    }
  }

  async function importTitle(item: MediaResult) {
    const key = `${item.media_type}:${item.external_id}`;
    setImporting(key);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/v1/media/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "tmdb",
          external_id: Number(item.external_id),
          media_type: item.media_type,
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(readError(body?.detail));
      if (!body || typeof body !== "object") {
        throw new Error("The library service returned an invalid response.");
      }
      setAdded((previous) => new Set(previous).add(key));
      setNotice(
        body.already_in_library
          ? `${item.title} is already in your library.`
          : `Added ${item.title} to your library.`,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "This title could not be added. Please try again.",
      );
    } finally {
      setImporting(null);
    }
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">FIND YOUR NEXT WATCH</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Discover
        </h1>
        <p className="mt-2 text-sm text-zinc-400">
          Search the TMDB catalog and add a film or show to your library.
        </p>
      </div>

      <form className="panel flex flex-col gap-3 p-3 sm:flex-row" onSubmit={search}>
        <label className="flex h-11 min-w-0 flex-1 items-center gap-3 px-2">
          <Search className="shrink-0 text-zinc-500" size={18} />
          <span className="sr-only">Search movies and TV shows</span>
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search movies and TV shows"
            value={query}
          />
        </label>
        <div className="flex gap-2">
          <label className="sr-only" htmlFor="media-type">
            Filter by media type
          </label>
          <select
            className="h-11 flex-1 rounded-lg border border-white/[0.07] bg-[#111114] px-3 text-xs text-zinc-300 outline-none focus:border-violet-400/40 sm:flex-none"
            id="media-type"
            onChange={(event) => setMediaKind(event.target.value as MediaKind)}
            value={mediaKind}
          >
            <option value="ALL">All titles</option>
            <option value="MOVIE">Movies</option>
            <option value="TV">TV shows</option>
          </select>
          <button
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-violet-400 px-4 text-xs font-semibold text-[#111014] transition-colors hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
            type="submit"
          >
            {loading ? <LoaderCircle className="animate-spin" size={15} /> : <Search size={15} />}
            Search
          </button>
        </div>
      </form>

      {(error || notice) && (
        <p
          aria-live="polite"
          className={`rounded-lg border px-4 py-3 text-sm ${
            error
              ? "border-red-400/15 bg-red-400/[0.04] text-red-200"
              : "border-emerald-400/15 bg-emerald-400/[0.04] text-emerald-200"
          }`}
          role={error ? "alert" : "status"}
        >
          {error || notice}
        </p>
      )}

      {results.length > 0 ? (
        <section aria-label="Search results" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {results.map((item) => {
            const key = `${item.media_type}:${item.external_id}`;
            const isImporting = importing === key;
            const isAdded = added.has(key);
            return (
              <article
                className="panel overflow-hidden p-3 transition-colors hover:border-white/[0.11]"
                key={key}
              >
                <div className="flex min-h-40">
                  <button
                    aria-expanded={expandedKey === key}
                    aria-label={`${expandedKey === key ? "Collapse" : "Expand"} details for ${item.title}`}
                    className="relative min-h-32 w-[88px] shrink-0 overflow-hidden rounded-lg bg-zinc-800 text-left"
                    onClick={() => void toggleDetails(item, key)}
                    type="button"
                  >
                    {item.poster_path ? (
                      <div
                        aria-label={`${item.title} poster`}
                        className="absolute inset-0 bg-cover bg-center"
                        role="img"
                        style={{ backgroundImage: `url("${item.poster_path}")` }}
                      />
                    ) : (
                      <div className="grid h-full min-h-32 place-items-center text-zinc-600">
                        {item.media_type === "MOVIE" ? <Film size={22} /> : <Tv2 size={22} />}
                      </div>
                    )}
                  </button>
                  <div className="flex min-w-0 flex-1 flex-col pl-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <p className="eyebrow">
                        {item.media_type === "MOVIE" ? "MOVIE" : "TV SHOW"}
                        {(item.release_date || item.first_air_date) &&
                          ` · ${(item.release_date || item.first_air_date)?.slice(0, 4)}`}
                      </p>
                      <RatingBadge score={item.tmdb_rating} source="TMDB" />
                    </div>
                    <button
                      aria-expanded={expandedKey === key}
                      className="mt-2 flex w-full items-center justify-between gap-2 text-left"
                      onClick={() => void toggleDetails(item, key)}
                      type="button"
                    >
                      <span className="line-clamp-1 text-sm font-medium text-zinc-100">
                        {item.title}
                      </span>
                      <ChevronDown
                        className={`shrink-0 text-zinc-500 transition-transform ${
                          expandedKey === key ? "rotate-180" : ""
                        }`}
                        size={15}
                      />
                    </button>
                    <p
                      className={`mt-1.5 text-xs leading-5 text-zinc-500 ${
                        expandedKey === key ? "" : "line-clamp-3"
                      }`}
                    >
                      {item.overview || "No description is available for this title."}
                    </p>
                    <button
                      className="mt-auto inline-flex w-fit items-center gap-1.5 pt-3 text-xs font-medium text-violet-300 transition-colors hover:text-violet-200 disabled:text-zinc-500"
                      disabled={isImporting || isAdded}
                      onClick={() => importTitle(item)}
                      type="button"
                    >
                      {isImporting ? (
                        <LoaderCircle className="animate-spin" size={13} />
                      ) : (
                        <ArrowDownToLine size={13} />
                      )}
                      {isAdded ? "In your library" : "Add to library"}
                    </button>
                  </div>
                </div>
                {expandedKey === key && (
                  <MediaRatings
                    error={ratingsError}
                    loading={ratingsLoading === key}
                    mediaType={item.media_type}
                    ratings={ratingsByKey[key] ?? null}
                    title={item.title}
                    tmdbId={item.external_id}
                  />
                )}
              </article>
            );
          })}
        </section>
      ) : (
        <div className="panel flex min-h-64 flex-col items-center justify-center px-6 text-center">
          <div className="grid size-12 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-zinc-500">
            <Search size={19} />
          </div>
          <h2 className="mt-4 text-sm font-medium text-zinc-200">
            {loading ? "Looking across the catalog…" : "A world of stories, one search away"}
          </h2>
          <p className="mt-2 max-w-sm text-xs leading-5 text-zinc-500">
            {loading
              ? "This can take a moment."
              : "Search for a title to see its details and save it to your personal library."}
          </p>
        </div>
      )}
    </div>
  );
}

function readError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  return "The request could not be completed. Please try again.";
}
