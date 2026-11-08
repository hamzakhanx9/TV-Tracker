"use client";

import { ArrowLeft, LoaderCircle, Save, Star } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { MediaRatings, type Ratings } from "@/components/media-ratings";

type MediaKind = "MOVIE" | "TV";
type WatchStatus = "PLAN_TO_WATCH" | "WATCHING" | "COMPLETED" | "ON_HOLD" | "DROPPED";

type LibraryTitleDetail = {
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
  };
  watch_status: WatchStatus;
  watched: boolean;
  watched_at: string | null;
  personal_rating: number | null;
  personal_review: string | null;
  personal_notes: string | null;
};

const statusLabels: Record<WatchStatus, string> = {
  PLAN_TO_WATCH: "Plan to watch",
  WATCHING: "Watching",
  COMPLETED: "Completed",
  ON_HOLD: "On hold",
  DROPPED: "Dropped",
};

export function MediaDetail({ mediaId }: { mediaId: string }) {
  const [detail, setDetail] = useState<LibraryTitleDetail | null>(null);
  const [ratings, setRatings] = useState<Ratings | null>(null);
  const [rating, setRating] = useState("");
  const [review, setReview] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [ratingsError, setRatingsError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/library/${mediaId}`, { cache: "no-store" });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not load this title.",
        );
      }
      const loaded = body as LibraryTitleDetail;
      setDetail(loaded);
      setRating(loaded.personal_rating?.toString() ?? "");
      setReview(loaded.personal_review ?? "");
      setNotes(loaded.personal_notes ?? "");
      try {
        const ratingsResponse = await fetch(`/api/v1/library/${mediaId}/ratings`);
        const ratingsBody = await ratingsResponse.json().catch(() => null);
        if (!ratingsResponse.ok) {
          throw new Error(
            typeof ratingsBody?.detail === "string"
              ? ratingsBody.detail
              : "Could not load provider ratings.",
          );
        }
        setRatings(ratingsBody as Ratings);
      } catch (ratingsLoadError) {
        setRatingsError(
          ratingsLoadError instanceof Error
            ? ratingsLoadError.message
            : "Could not load provider ratings.",
        );
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load this title.");
    } finally {
      setLoading(false);
    }
  }, [mediaId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  async function saveFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const response = await fetch(`/api/v1/library/${mediaId}/feedback`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          personal_rating: rating ? Number(rating) : null,
          personal_review: review || null,
          personal_notes: notes || null,
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not save your feedback.",
        );
      }
      const updated = body as LibraryTitleDetail;
      setDetail(updated);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save your feedback.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="panel flex min-h-64 items-center justify-center text-zinc-500">
        <LoaderCircle className="animate-spin" size={18} />
        <span className="ml-3 text-sm">Loading title…</span>
      </div>
    );
  }

  if (!detail) {
    return (
      <section className="panel p-6">
        <p aria-live="polite" className="text-sm text-red-300" role="alert">
          {error}
        </p>
        <Link className="subtle-link mt-5 inline-flex items-center gap-2" href="/discover">
          <ArrowLeft size={14} />
          Back to discover
        </Link>
      </section>
    );
  }

  const media = detail.media;
  const year = (media.release_date || media.first_air_date)?.slice(0, 4);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link
        className="subtle-link inline-flex items-center gap-2"
        href={media.media_type === "TV" ? "/tv" : "/movies"}
      >
        <ArrowLeft size={14} />
        Back to {media.media_type === "TV" ? "TV shows" : "movies"}
      </Link>
      <section className="panel overflow-hidden">
        <div className="grid gap-6 p-5 sm:grid-cols-[200px_minmax(0,1fr)] sm:p-7">
          <div
            aria-label={`${media.title} poster`}
            className="aspect-[2/3] rounded-xl bg-zinc-900 bg-cover bg-center"
            role="img"
            style={media.poster_path ? { backgroundImage: `url("${media.poster_path}")` } : {}}
          />
          <div>
            <p className="eyebrow">
              {media.media_type === "TV" ? "TV SERIES" : "MOVIE"}
              {year ? ` · ${year}` : ""}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
              {media.title}
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              {media.overview || "No description is available for this title."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-white/[0.08] px-3 py-1.5 text-zinc-300">
                {statusLabels[detail.watch_status]}
              </span>
              {detail.watched && (
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-3 py-1.5 text-emerald-200">
                  Watched
                </span>
              )}
            </div>
            <MediaRatings
              error={ratingsError}
              loading={false}
              mediaType={media.media_type}
              ratings={ratings}
              title={media.title}
              tmdbId={ratings?.tmdb_id ?? ""}
            />
          </div>
        </div>
      </section>

      <form className="panel space-y-5 p-5 sm:p-7" onSubmit={saveFeedback}>
        <div>
          <p className="eyebrow">YOUR TAKE</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Personal Rating & Review</h2>
        </div>
        <label className="block max-w-xs text-sm text-zinc-300">
          Your rating (1–10)
          <span className="mt-2 flex items-center gap-2">
            <Star className="text-amber-300" size={16} />
            <input
              className="h-10 w-full rounded-lg border border-white/[0.08] bg-black/20 px-3 text-sm text-white outline-none focus:border-violet-400/50"
              max="10"
              min="1"
              onChange={(event) => setRating(event.target.value)}
              placeholder="Not rated"
              step="0.5"
              type="number"
              value={rating}
            />
          </span>
        </label>
        <label className="block text-sm text-zinc-300">
          Review
          <textarea
            className="mt-2 min-h-32 w-full rounded-lg border border-white/[0.08] bg-black/20 p-3 text-sm leading-6 text-white outline-none focus:border-violet-400/50"
            maxLength={10000}
            onChange={(event) => setReview(event.target.value)}
            placeholder="What did you think?"
            value={review}
          />
        </label>
        <label className="block text-sm text-zinc-300">
          Private notes
          <textarea
            className="mt-2 min-h-24 w-full rounded-lg border border-white/[0.08] bg-black/20 p-3 text-sm leading-6 text-white outline-none focus:border-violet-400/50"
            maxLength={5000}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Keep a note for yourself…"
            value={notes}
          />
        </label>
        {error && (
          <p aria-live="polite" className="text-sm text-red-300" role="alert">
            {error}
          </p>
        )}
        {saved && <p className="text-sm text-emerald-300">Your feedback has been saved.</p>}
        <button
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-violet-400 px-4 text-sm font-medium text-[#111114] transition-colors hover:bg-violet-300 disabled:opacity-50"
          disabled={saving}
          type="submit"
        >
          {saving ? <LoaderCircle className="animate-spin" size={15} /> : <Save size={15} />}
          Save feedback
        </button>
      </form>
    </div>
  );
}
