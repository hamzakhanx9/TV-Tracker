"use client";

import { ExternalLink, LoaderCircle, Star } from "lucide-react";

export type Ratings = {
  tmdb_id: string;
  tmdb_rating: number | null;
  tmdb_vote_count: number | null;
  imdb_rating: number | null;
  rotten_tomatoes_rating: number | null;
  imdb_id: string | null;
  omdb_configured: boolean;
  omdb_available: boolean;
};

type MediaKind = "MOVIE" | "TV";

export function RatingBadge({
  source,
  score,
  suffix = "/10",
  showSource = true,
}: {
  source: string;
  score: number | null;
  suffix?: string;
  showSource?: boolean;
}) {
  if (score === null) return null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.07] bg-white/[0.035] px-2 py-1 text-[11px] text-zinc-300">
      <Star className="fill-amber-300 text-amber-300" size={12} />
      <span className="font-medium text-zinc-100">{score}</span>
      <span className="text-zinc-500">{suffix}</span>
      {showSource && <span className="text-zinc-500">{source}</span>}
    </span>
  );
}

export function MediaRatings({
  ratings,
  loading,
  error,
  title,
  mediaType,
  tmdbId,
}: {
  ratings: Ratings | null;
  loading: boolean;
  error: string | null;
  title: string;
  mediaType: MediaKind;
  tmdbId: string;
}) {
  const seriesGraphUrl = makeSeriesGraphUrl(tmdbId, title);

  return (
    <div className="mt-4 space-y-4 border-t border-white/[0.07] pt-4">
      <div>
        <p className="eyebrow">RATINGS</p>
        {loading ? (
          <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
            <LoaderCircle className="animate-spin" size={14} /> Loading ratings…
          </div>
        ) : error ? (
          <p className="mt-2 text-xs text-amber-200">{error}</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            <RatingBadge score={ratings?.tmdb_rating ?? null} source="TMDB" />
            <RatingBadge score={ratings?.imdb_rating ?? null} source="IMDb" />
            <RatingBadge
              score={ratings?.rotten_tomatoes_rating ?? null}
              source="RT"
              suffix="%"
            />
            {ratings && !ratings.omdb_configured && (
              <span className="self-center text-[10px] text-zinc-600">
                Add OMDB_API_KEY for IMDb and Rotten Tomatoes ratings
              </span>
            )}
            {ratings &&
              ratings.omdb_configured &&
              ratings.imdb_rating === null &&
              ratings.rotten_tomatoes_rating === null && (
                <span className="self-center text-[10px] text-zinc-600">
                  {ratings.omdb_available
                    ? "No external ratings available"
                    : "Could not load external ratings"}
                </span>
              )}
          </div>
        )}
        {ratings?.tmdb_vote_count ? (
          <p className="mt-2 text-[10px] text-zinc-600">
            TMDB rating from {ratings.tmdb_vote_count.toLocaleString()} votes
          </p>
        ) : null}
      </div>

      {mediaType === "TV" && (
        <div>
          <a
            className="inline-flex items-center gap-1.5 text-[11px] text-zinc-400 hover:text-zinc-200"
            href={seriesGraphUrl}
            rel="noreferrer"
            target="_blank"
          >
            View on SeriesGraph <ExternalLink size={12} />
          </a>
        </div>
      )}
    </div>
  );
}

function makeSeriesGraphUrl(tmdbId: string, title: string): string {
  const slug =
    title
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "show";
  return `https://seriesgraph.com/show/${encodeURIComponent(tmdbId)}-${slug}`;
}
