"use client";

import {
  Check,
  Clapperboard,
  ChevronDown,
  ArrowUpRight,
  Eye,
  EyeOff,
  Film,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Trash2,
  Tv2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { MediaRatings, RatingBadge, type Ratings } from "@/components/media-ratings";

type MediaKind = "MOVIE" | "TV";
type WatchStatus = "PLAN_TO_WATCH" | "WATCHING" | "COMPLETED" | "ON_HOLD" | "DROPPED";

type LibraryItem = {
  media: {
    id: string;
    media_type: MediaKind;
    title: string;
    overview: string | null;
    release_date: string | null;
    first_air_date: string | null;
    poster_path: string | null;
    runtime: number | null;
    tmdb_rating: number | null;
    tmdb_vote_count: number | null;
    imdb_rating: number | null;
    rotten_tomatoes_rating: number | null;
  };
  watch_status: WatchStatus;
  added_at: string;
  watched: boolean;
  watched_at: string | null;
};

type TrackingEpisode = {
  id: string;
  season_number: number;
  episode_number: number | null;
  title: string;
  overview: string | null;
  air_at: string | null;
  air_date: string | null;
  runtime: number | null;
  still_path: string | null;
  watched: boolean;
  watched_at: string | null;
};

type TrackingSeason = {
  id: string;
  season_number: number;
  name: string;
  episodes: TrackingEpisode[];
  watched_count: number;
  episode_count: number;
};

type MediaTracking = {
  media_id: string;
  seasons: TrackingSeason[];
  watched_count: number;
  episode_count: number;
  tvmaze_available: boolean;
};

const statuses: { value: WatchStatus; label: string }[] = [
  { value: "PLAN_TO_WATCH", label: "Plan to watch" },
  { value: "WATCHING", label: "Watching" },
  { value: "COMPLETED", label: "Completed" },
  { value: "ON_HOLD", label: "On hold" },
  { value: "DROPPED", label: "Dropped" },
];

export function MediaLibrary({
  mediaType,
  initialFilter = "ALL",
  title,
  showStatusFilter = true,
}: {
  mediaType: MediaKind | "ALL";
  initialFilter?: WatchStatus | "ALL";
  title?: string;
  showStatusFilter?: boolean;
}) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);
  const [filter, setFilter] = useState<WatchStatus | "ALL">(initialFilter);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [tvDialogId, setTvDialogId] = useState<string | null>(null);
  const tvDialogRef = useRef<HTMLDialogElement>(null);
  const [ratingsById, setRatingsById] = useState<Record<string, Ratings>>({});
  const [ratingsLoading, setRatingsLoading] = useState<string | null>(null);
  const [ratingsError, setRatingsError] = useState<string | null>(null);
  const [trackingById, setTrackingById] = useState<Record<string, MediaTracking>>({});
  const [trackingLoading, setTrackingLoading] = useState<string | null>(null);
  const [trackingUpdating, setTrackingUpdating] = useState<string | null>(null);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [revealedEpisodes, setRevealedEpisodes] = useState<Set<string>>(new Set());
  const isMovie = mediaType === "MOVIE";

  const loadLibrary = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const mediaTypeQuery = mediaType === "ALL" ? "" : `?media_type=${mediaType}`;
      const response = await fetch(`/api/v1/library${mediaTypeQuery}`, {
        cache: "no-store",
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not load library.",
        );
      }
      if (!Array.isArray(body)) throw new Error("The library service returned an invalid response.");
      setItems(body as LibraryItem[]);
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : "Could not load library. Please retry.",
      );
    } finally {
      setLoading(false);
    }
  }, [mediaType]);

  useEffect(() => {
    void loadLibrary();
  }, [loadLibrary]);

  useEffect(() => {
    const dialog = tvDialogRef.current;
    if (tvDialogId && dialog && !dialog.open) dialog.showModal();
    else if (!tvDialogId && dialog?.open) dialog.close();
  }, [tvDialogId]);

  async function changeStatus(item: LibraryItem, watchStatus: WatchStatus) {
    setUpdating(item.media.id);
    setError("");
    try {
      const response = await fetch(`/api/v1/library/${item.media.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watch_status: watchStatus }),
      });
      if (!response.ok) throw new Error("Could not update status. Please try again.");
      setItems((current) =>
        current.map((entry) =>
          entry.media.id === item.media.id ? { ...entry, watch_status: watchStatus } : entry,
        ),
      );
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Could not update status.");
    } finally {
      setUpdating(null);
    }
  }

  async function removeItem(item: LibraryItem) {
    setUpdating(item.media.id);
    setError("");
    try {
      const response = await fetch(`/api/v1/library/${item.media.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not remove this title. Please try again.");
      setItems((current) => current.filter((entry) => entry.media.id !== item.media.id));
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Could not remove title.");
    } finally {
      setUpdating(null);
    }
  }

  async function loadTracking(item: LibraryItem, forceSync = false) {
    const id = item.media.id;
    setTrackingLoading(id);
    setTrackingError(null);
    try {
      let response = await fetch(
        forceSync
          ? `/api/v1/library/${id}/episodes/sync`
          : `/api/v1/library/${id}/episodes`,
        { method: forceSync ? "POST" : "GET", cache: "no-store" },
      );
      let body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not load episode tracking.",
        );
      }
      let tracking = body as MediaTracking;
      if (!forceSync && tracking.tvmaze_available && tracking.episode_count === 0) {
        response = await fetch(`/api/v1/library/${id}/episodes/sync`, { method: "POST" });
        body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not sync episode list.",
          );
        }
        tracking = body as MediaTracking;
      }
      setTrackingById((current) => ({ ...current, [id]: tracking }));
    } catch (loadError) {
      setTrackingError(
        loadError instanceof Error ? loadError.message : "Could not load episode tracking.",
      );
    } finally {
      setTrackingLoading(null);
    }
  }

  async function setMovieWatched(item: LibraryItem, watched: boolean) {
    const id = item.media.id;
    setUpdating(id);
    setError("");
    try {
      const response = await fetch(`/api/v1/library/${id}/watched`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watched }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not update watch progress.",
        );
      }
      setItems((current) =>
        current.map((entry) =>
          entry.media.id === id
            ? {
                ...entry,
                watched: body.watched,
                watched_at: body.watched_at,
                watch_status: body.watch_status,
              }
            : entry,
        ),
      );
    } catch (updateError) {
      setError(
        updateError instanceof Error ? updateError.message : "Could not update watch progress.",
      );
    } finally {
      setUpdating(null);
    }
  }

  async function logRewatch(item: LibraryItem, episodeId?: string) {
    const id = item.media.id;
    setTrackingError(null);
    setError("");
    setTrackingUpdating(episodeId ?? id);
    try {
      const response = await fetch(
        episodeId
          ? `/api/v1/episodes/${episodeId}/rewatch`
          : `/api/v1/library/${id}/rewatch`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idempotency_key: crypto.randomUUID() }),
        },
      );
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not log this rewatch.",
        );
      }
      if (episodeId) {
        await loadTracking(item);
      } else {
        setItems((current) =>
          current.map((entry) =>
            entry.media.id === id
              ? { ...entry, watched: body.watched, watched_at: body.watched_at }
              : entry,
          ),
        );
      }
    } catch (rewatchError) {
      const message =
        rewatchError instanceof Error ? rewatchError.message : "Could not log this rewatch.";
      if (episodeId) setTrackingError(message);
      else setError(message);
    } finally {
      setTrackingUpdating(null);
    }
  }

  async function setEpisodeWatched(
    item: LibraryItem,
    episodeId: string,
    watched: boolean,
  ) {
    setTrackingUpdating(episodeId);
    setTrackingError(null);
    try {
      const response = await fetch(`/api/v1/episodes/${episodeId}/watched`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watched }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not update episode progress.",
        );
      }
      await loadTracking(item);
    } catch (updateError) {
      setTrackingError(
        updateError instanceof Error
          ? updateError.message
          : "Could not update episode progress.",
      );
    } finally {
      setTrackingUpdating(null);
    }
  }

  async function setSeasonWatched(item: LibraryItem, season: TrackingSeason, watched: boolean) {
    setTrackingUpdating(season.id);
    setTrackingError(null);
    try {
      const response = await fetch(`/api/v1/seasons/${season.id}/watched`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watched }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not update season progress.",
        );
      }
      setTrackingById((current) => ({ ...current, [item.media.id]: body as MediaTracking }));
    } catch (updateError) {
      setTrackingError(
        updateError instanceof Error
          ? updateError.message
          : "Could not update season progress.",
      );
    } finally {
      setTrackingUpdating(null);
    }
  }

  async function toggleDetails(item: LibraryItem) {
    const id = item.media.id;
    if (item.media.media_type === "TV") {
      setTvDialogId((current) => (current === id ? null : id));
    } else {
      setExpandedId((current) => (current === id ? null : id));
    }
    setRatingsError(null);
    setTrackingError(null);
    if (item.media.media_type === "TV" && !trackingById[id]) {
      void loadTracking(item);
    }
    if (ratingsById[id]) return;

    setRatingsLoading(id);
    try {
      const response = await fetch(`/api/v1/library/${id}/ratings`);
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not load title ratings.",
        );
      }
      const ratings = body as Ratings;
      setRatingsById((current) => ({ ...current, [id]: ratings }));
      setItems((current) =>
        current.map((entry) =>
          entry.media.id === id
            ? {
                ...entry,
                media: {
                  ...entry.media,
                  tmdb_rating: ratings.tmdb_rating,
                  tmdb_vote_count: ratings.tmdb_vote_count,
                  imdb_rating: ratings.imdb_rating,
                  rotten_tomatoes_rating: ratings.rotten_tomatoes_rating,
                },
              }
            : entry,
        ),
      );
    } catch (loadError) {
      setRatingsError(
        loadError instanceof Error ? loadError.message : "Could not load title ratings.",
      );
    } finally {
      setRatingsLoading(null);
    }
  }

  const visibleItems = items.filter((item) => filter === "ALL" || item.watch_status === filter);
  const selectedTvItem = items.find((item) => item.media.id === tvDialogId) ?? null;
  const collectionTitle =
    title ?? (mediaType === "ALL" ? "Watchlist" : isMovie ? "Movies" : "TV shows");

  return (
    <div className="space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">YOUR COLLECTION</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            {collectionTitle}
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            {visibleItems.length} {title ? "titles" : isMovie ? "films" : "shows"}{" "}
            {title ? "to watch" : "in your library"}
          </p>
        </div>
        {showStatusFilter && (
          <label className="flex items-center gap-3 text-xs text-zinc-500">
            Status
            <select
              className="h-10 rounded-lg border border-white/[0.07] bg-[#111114] px-3 text-xs text-zinc-300 outline-none focus:border-violet-400/40"
              onChange={(event) => setFilter(event.target.value as WatchStatus | "ALL")}
              value={filter}
            >
              <option value="ALL">All statuses</option>
              {statuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {error && (
        <p
          aria-live="polite"
          className="rounded-lg border border-red-400/15 bg-red-400/[0.04] px-4 py-3 text-sm text-red-200"
          role="alert"
        >
          {error}
        </p>
      )}

      {loading ? (
        <div className="panel flex min-h-64 items-center justify-center text-zinc-500">
          <LoaderCircle className="animate-spin" size={20} />
          <span className="ml-3 text-sm">Loading your library…</span>
        </div>
      ) : visibleItems.length === 0 ? (
        <div className="panel flex min-h-72 flex-col items-center justify-center px-6 text-center">
          <div className="grid size-12 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-zinc-500">
            {mediaType === "ALL" ? (
              <Clapperboard size={20} />
            ) : isMovie ? (
              <Film size={20} />
            ) : (
              <Tv2 size={20} />
            )}
          </div>
          <h2 className="mt-4 text-sm font-medium text-zinc-200">
            {items.length === 0
              ? title
                ? "Your watchlist is empty"
                : `Your ${isMovie ? "movie" : "TV"} library is ready`
              : title
                ? "Nothing waiting in your watchlist"
                : "Nothing in this status yet"}
          </h2>
          <p className="mt-2 max-w-sm text-xs leading-5 text-zinc-500">
            {items.length === 0
              ? title
                ? "Add a movie or show to your library and set its status to Plan to watch."
                : "Discover a title and add it to your library to get started."
              : title
                ? "Titles with a different status are not in your watchlist. Set a title to Plan to watch to add it here."
              : "Choose another status to see more of your collection."}
          </p>
          {items.length === 0 && (
            <Link className="subtle-link mt-4" href="/discover">
              Discover titles
            </Link>
          )}
        </div>
      ) : (
        <section aria-label={`${collectionTitle} in your library`}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {visibleItems.map((item) => (
              <article className="panel group overflow-hidden" key={item.media.id}>
                <button
                  aria-expanded={
                    item.media.media_type === "TV"
                      ? tvDialogId === item.media.id
                      : expandedId === item.media.id
                  }
                  aria-label={`Open ${item.media.media_type === "TV" ? "episode tracker" : "details"} for ${item.media.title}`}
                  className="relative block aspect-[2/3] w-full overflow-hidden bg-zinc-900 text-left"
                  onClick={() => void toggleDetails(item)}
                  type="button"
                >
                  {item.media.poster_path ? (
                    <div
                      aria-label={`${item.media.title} poster`}
                      className="absolute inset-0 bg-cover bg-center"
                      role="img"
                      style={{ backgroundImage: `url("${item.media.poster_path}")` }}
                    />
                  ) : (
                    <div className="grid h-full place-items-center text-zinc-700">
                      {item.media.media_type === "MOVIE" ? (
                        <Film size={32} />
                      ) : (
                        <Tv2 size={32} />
                      )}
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-0 flex flex-col items-start bg-gradient-to-t from-black/95 via-black/50 to-transparent p-3 pt-12">
                    <span className="line-clamp-1 text-sm font-medium text-white">
                      {item.media.title}
                    </span>
                    <span className="mt-1 flex w-full items-center justify-between gap-2 text-[10px] text-zinc-300">
                      {(item.media.release_date || item.media.first_air_date)?.slice(0, 4) ??
                        "Release date unknown"}
                      <ChevronDown
                        className={`transition-transform ${
                          (expandedId === item.media.id || tvDialogId === item.media.id)
                            ? "rotate-180"
                            : ""
                        }`}
                        size={14}
                      />
                    </span>
                  </div>
                  {updating === item.media.id && (
                    <div className="absolute inset-0 grid place-items-center bg-black/55 text-white">
                      <LoaderCircle className="animate-spin" size={20} />
                    </div>
                  )}
                </button>
                <div className="flex items-center justify-between gap-2 p-2.5">
                  <RatingBadge
                    score={item.media.tmdb_rating}
                    source="TMDB"
                  />
                  {item.media.tmdb_rating === null && (
                    <span className="text-[10px] text-zinc-600">No rating</span>
                  )}
                  <label className="min-w-0 flex-1">
                    <span className="sr-only">Status for {item.media.title}</span>
                    <select
                      className="h-9 w-full rounded-md border border-white/[0.07] bg-[#111114] px-2 text-[10px] text-zinc-300 outline-none focus:border-violet-400/40"
                      disabled={updating === item.media.id}
                      onChange={(event) =>
                        void changeStatus(item, event.target.value as WatchStatus)
                      }
                      value={item.watch_status}
                    >
                      {statuses.map((status) => (
                        <option key={status.value} value={status.value}>
                          {status.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    aria-label={`Remove ${item.media.title} from library`}
                    className="grid size-9 shrink-0 place-items-center rounded-md text-zinc-500 transition-colors hover:bg-red-400/10 hover:text-red-300 disabled:opacity-50"
                    disabled={updating === item.media.id}
                    onClick={() => void removeItem(item)}
                    type="button"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                {expandedId === item.media.id && item.media.media_type === "MOVIE" && (
                  <div className="px-3 pb-3">
                    <p className="line-clamp-5 text-xs leading-5 text-zinc-400">
                      {item.media.overview || "No description is available for this title."}
                    </p>
                    <MediaRatings
                      error={ratingsError}
                      loading={ratingsLoading === item.media.id}
                      mediaType={item.media.media_type}
                      ratings={ratingsById[item.media.id] ?? null}
                      title={item.media.title}
                      tmdbId={ratingsById[item.media.id]?.tmdb_id ?? ""}
                    />
                    <Link
                      className="subtle-link mt-3 inline-flex items-center gap-1"
                      href={`/media/${item.media.id}`}
                    >
                      Full details and your review <ArrowUpRight size={13} />
                    </Link>
                    {isMovie ? (
                      <div className="mt-4 flex gap-2">
                        <button
                          className="flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] text-xs font-medium text-zinc-200 transition-colors hover:bg-white/[0.07] disabled:opacity-50"
                          disabled={updating === item.media.id}
                          onClick={() => void setMovieWatched(item, !item.watched)}
                          type="button"
                        >
                          <Check size={14} />
                          {item.watched ? "Mark unwatched" : "Mark watched"}
                        </button>
                        {item.watched && (
                          <button
                            aria-label={`Log a rewatch of ${item.media.title}`}
                            className="grid size-9 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-zinc-400 hover:bg-white/[0.07] hover:text-zinc-200 disabled:opacity-50"
                            disabled={
                              updating === item.media.id ||
                              trackingUpdating === item.media.id
                            }
                            onClick={() => void logRewatch(item)}
                            title="Log rewatch"
                            type="button"
                          >
                            <RotateCcw size={14} />
                          </button>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
      <dialog
        aria-labelledby="tv-tracking-title"
        className="fixed inset-0 m-0 h-dvh max-h-dvh w-screen max-w-none border-0 bg-transparent p-0 text-zinc-100 backdrop:bg-black/80 open:flex"
        onClick={(event) => {
          if (event.target === event.currentTarget) tvDialogRef.current?.close();
        }}
        onClose={() => setTvDialogId(null)}
        ref={tvDialogRef}
      >
        {selectedTvItem && (
          <div className="relative m-auto flex max-h-[92dvh] w-[min(1000px,96vw)] flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#111114] shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-white/[0.07] px-5 py-4 sm:px-7">
              <div className="min-w-0">
                <p className="eyebrow">SERIES TRACKING</p>
                <h2
                  className="mt-1 truncate text-xl font-semibold text-white sm:text-2xl"
                  id="tv-tracking-title"
                >
                  {selectedTvItem.media.title}
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  {trackingById[selectedTvItem.media.id]
                    ? `${trackingById[selectedTvItem.media.id].watched_count} of ${trackingById[selectedTvItem.media.id].episode_count} episodes watched`
                    : "Track watched episodes and season progress"}
                </p>
                <Link
                  className="mt-2 inline-flex items-center gap-1 text-xs text-violet-300 hover:text-violet-200"
                  href={`/media/${selectedTvItem.media.id}`}
                >
                  Full details and your review <ArrowUpRight size={13} />
                </Link>
              </div>
              <button
                aria-label="Close episode tracker"
                autoFocus
                className="grid size-9 shrink-0 place-items-center rounded-lg border border-white/[0.08] text-zinc-400 hover:bg-white/[0.06] hover:text-white"
                onClick={() => tvDialogRef.current?.close()}
                type="button"
              >
                <X size={17} />
              </button>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-7">
              <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
                <section>
                  <p className="text-sm leading-6 text-zinc-400">
                    {selectedTvItem.media.overview || "No description is available for this show."}
                  </p>
                  <MediaRatings
                    error={ratingsError}
                    loading={ratingsLoading === selectedTvItem.media.id}
                    mediaType="TV"
                    ratings={ratingsById[selectedTvItem.media.id] ?? null}
                    title={selectedTvItem.media.title}
                    tmdbId={ratingsById[selectedTvItem.media.id]?.tmdb_id ?? ""}
                  />
                </section>
                <section
                  aria-label={`Episode tracking for ${selectedTvItem.media.title}`}
                  className="rounded-xl border border-white/[0.07] bg-black/10 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100">
                        Seasons & episodes
                      </h3>
                      {trackingById[selectedTvItem.media.id] && (
                        <p className="mt-1 text-xs text-zinc-500">
                          {trackingById[selectedTvItem.media.id].watched_count} of{" "}
                          {trackingById[selectedTvItem.media.id].episode_count} watched
                        </p>
                      )}
                    </div>
                    <button
                      aria-label={`Sync episodes for ${selectedTvItem.media.title}`}
                      className="grid size-9 shrink-0 place-items-center rounded-lg border border-white/[0.08] text-zinc-400 hover:bg-white/[0.06] hover:text-white disabled:opacity-50"
                      disabled={
                        trackingLoading === selectedTvItem.media.id ||
                        !trackingById[selectedTvItem.media.id]?.tvmaze_available
                      }
                      onClick={() => void loadTracking(selectedTvItem, true)}
                      title="Sync episode list"
                      type="button"
                    >
                      {trackingLoading === selectedTvItem.media.id ? (
                        <LoaderCircle className="animate-spin" size={15} />
                      ) : (
                        <RefreshCw size={15} />
                      )}
                    </button>
                  </div>
                  {trackingError && (
                    <p aria-live="polite" className="mt-3 text-xs text-red-300" role="alert">
                      {trackingError}
                    </p>
                  )}
                  {trackingLoading === selectedTvItem.media.id &&
                  !trackingById[selectedTvItem.media.id] ? (
                    <div className="flex items-center gap-2 py-8 text-sm text-zinc-500">
                      <LoaderCircle className="animate-spin" size={15} />
                      Loading episodes…
                    </div>
                  ) : trackingById[selectedTvItem.media.id]?.seasons.length ? (
                    <div className="mt-4 max-h-[55dvh] space-y-3 overflow-y-auto pr-1">
                      {trackingById[selectedTvItem.media.id].seasons.map((season) => (
                        <div
                          className="rounded-lg border border-white/[0.06] bg-[#17171b] p-3 sm:p-4"
                          key={season.id}
                        >
                          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <h4 className="text-xs font-medium text-zinc-200">
                                {season.name}
                              </h4>
                              <p className="mt-0.5 text-[10px] text-zinc-500">
                                {season.watched_count} / {season.episode_count} watched
                              </p>
                            </div>
                            <button
                              className="rounded-md px-2 py-1 text-[10px] text-violet-300 hover:bg-violet-400/10 disabled:opacity-50"
                              disabled={trackingUpdating === season.id}
                              onClick={() =>
                                void setSeasonWatched(
                                  selectedTvItem,
                                  season,
                                  season.watched_count === 0,
                                )
                              }
                              type="button"
                            >
                              {season.watched_count > 0
                                ? "Mark season unwatched"
                                : "Mark aired episodes watched"}
                            </button>
                          </div>
                          <ul className="divide-y divide-white/[0.05]">
                            {season.episodes.map((episode) => {
                              const revealed = revealedEpisodes.has(episode.id);
                              return (
                                <li className="py-2 first:pt-1" key={episode.id}>
                                  <div className="flex items-start gap-2">
                                    <button
                                      aria-label={
                                        episode.watched
                                          ? `Mark ${episode.title} unwatched`
                                          : `Mark ${episode.title} watched`
                                      }
                                      className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded border ${
                                        episode.watched
                                          ? "border-violet-400/50 bg-violet-400/15 text-violet-200"
                                          : "border-white/10 text-transparent hover:border-violet-300/50"
                                      } disabled:opacity-50`}
                                      disabled={trackingUpdating === episode.id}
                                      onClick={() =>
                                        void setEpisodeWatched(
                                          selectedTvItem,
                                          episode.id,
                                          !episode.watched,
                                        )
                                      }
                                      type="button"
                                    >
                                      <Check size={12} />
                                    </button>
                                    <div className="min-w-0 flex-1">
                                      <p className="text-xs text-zinc-300">
                                        {episode.episode_number === null
                                          ? episode.title
                                          : `${season.season_number === 0 ? "Special" : `E${episode.episode_number}`} · ${episode.title}`}
                                      </p>
                                      {episode.overview && (
                                        <div className="mt-1">
                                          <button
                                            className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300"
                                            onClick={() =>
                                              setRevealedEpisodes((current) => {
                                                const next = new Set(current);
                                                if (revealed) next.delete(episode.id);
                                                else next.add(episode.id);
                                                return next;
                                              })
                                            }
                                            type="button"
                                          >
                                            {revealed ? (
                                              <EyeOff size={11} />
                                            ) : (
                                              <Eye size={11} />
                                            )}
                                            {revealed ? "Hide description" : "Reveal description"}
                                          </button>
                                          {revealed && (
                                            <p className="mt-1 text-[11px] leading-5 text-zinc-500">
                                              {episode.overview}
                                            </p>
                                          )}
                                        </div>
                                      )}
                                      {episode.watched && (
                                        <button
                                          className="mt-1 flex items-center gap-1 text-[10px] text-violet-300 hover:text-violet-200 disabled:opacity-50"
                                          disabled={trackingUpdating === episode.id}
                                          onClick={() =>
                                            void logRewatch(selectedTvItem, episode.id)
                                          }
                                          type="button"
                                        >
                                          <RotateCcw size={10} />
                                          Log rewatch
                                        </button>
                                      )}
                                    </div>
                                    <span className="shrink-0 text-[10px] text-zinc-600">
                                      {episode.air_date ?? "Date unknown"}
                                    </span>
                                  </div>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      ))}
                    </div>
                  ) : trackingById[selectedTvItem.media.id] ? (
                    <p className="mt-4 text-xs leading-5 text-zinc-500">
                      {trackingById[selectedTvItem.media.id].tvmaze_available
                        ? "No episodes are available yet. Use sync to try again."
                        : "Episode tracking needs a TVmaze match for this show."}
                    </p>
                  ) : null}
                </section>
              </div>
            </div>
          </div>
        )}
      </dialog>
    </div>
  );
}
