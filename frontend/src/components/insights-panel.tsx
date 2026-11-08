"use client";

import { AlertCircle, BookOpenText, Film, LoaderCircle, Star, StickyNote, Tv2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

type RatedTitle = {
  media: {
    id: string;
    media_type: "MOVIE" | "TV";
    title: string;
    poster_path: string | null;
    genres: string[];
  };
  personal_rating: number | null;
  personal_review: string | null;
  personal_notes: string | null;
};

function ratingLabel(rating: number) {
  return Number.isInteger(rating) ? String(rating) : rating.toFixed(1);
}

export function InsightsPanel() {
  const [titles, setTitles] = useState<RatedTitle[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadRatedTitles() {
      try {
        const response = await fetch("/api/v1/library", {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not load your insights.",
          );
        }
        if (!Array.isArray(body)) throw new Error("The library service returned invalid insights.");
        const ratedTitles = (body as RatedTitle[]).filter(
          (title) => title.personal_rating !== null,
        );
        setTitles(ratedTitles);
        setSelectedId((current) =>
          current && ratedTitles.some((title) => title.media.id === current)
            ? current
            : ratedTitles[0]?.media.id ?? null,
        );
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "Could not load your insights.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadRatedTitles();
    return () => controller.abort();
  }, []);

  const groups = useMemo(() => {
    const grouped = new Map<number, RatedTitle[]>();
    for (const title of titles) {
      if (title.personal_rating === null) continue;
      const current = grouped.get(title.personal_rating) ?? [];
      current.push(title);
      grouped.set(title.personal_rating, current);
    }
    return [...grouped.entries()].sort(([ratingA], [ratingB]) => ratingB - ratingA);
  }, [titles]);

  const selectedTitle = titles.find((title) => title.media.id === selectedId) ?? null;
  const averageRating =
    titles.length > 0
      ? titles.reduce((total, title) => total + (title.personal_rating ?? 0), 0) / titles.length
      : null;

  if (loading) {
    return (
      <div className="panel flex min-h-48 items-center justify-center gap-3 text-sm text-zinc-400">
        <LoaderCircle className="animate-spin" size={17} />
        Loading your opinions…
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

  return (
    <section className="space-y-7">
      <header>
        <p className="eyebrow">YOUR PERSONAL COLLECTION OF REVIEWS</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Your Insights</h1>
        <p className="mt-2 text-sm leading-6 text-zinc-400">
          The stories you’ve rated, and the thoughts you’ve saved about them.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="panel p-5">
          <p className="text-sm text-zinc-400">Titles you’ve rated</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-white">{titles.length}</p>
        </div>
        <div className="panel p-5">
          <p className="text-sm text-zinc-400">Your average rating</p>
          <p className="mt-2 flex items-center gap-2 text-3xl font-semibold tracking-tight text-white">
            {averageRating === null ? "—" : averageRating.toFixed(1)}
            {averageRating !== null && (
              <span className="text-sm font-normal text-zinc-500">out of 10</span>
            )}
          </p>
        </div>
      </div>

      {titles.length === 0 ? (
        <div className="panel flex min-h-64 flex-col items-center justify-center px-6 text-center">
          <Star className="text-amber-300" size={22} />
          <h2 className="mt-4 text-sm font-medium text-zinc-200">Your opinions start here</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">
            Rate a movie or show and add a review or private note. Your ratings and writing will
            gather here.
          </p>
        </div>
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
          <div className="space-y-4">
            {groups.map(([rating, ratedTitles]) => (
              <section
                aria-label={`Rated ${ratingLabel(rating)} out of 10`}
                className="panel p-4"
                key={rating}
              >
                <div className="mb-3 flex items-center gap-2">
                  <RatingStars rating={rating} />
                  <span className="text-xs font-medium tabular-nums text-amber-200">
                    {ratingLabel(rating)} / 10
                  </span>
                  <span className="text-xs text-zinc-500">
                    · {ratedTitles.length} {ratedTitles.length === 1 ? "title" : "titles"}
                  </span>
                </div>
                <ul className="space-y-1">
                  {ratedTitles.map((title) => {
                    const active = selectedId === title.media.id;
                    const Icon = title.media.media_type === "MOVIE" ? Film : Tv2;
                    return (
                      <li key={title.media.id}>
                        <button
                          aria-pressed={active}
                          className={`flex w-full items-center gap-3 rounded-xl p-2 text-left transition-colors ${active ? "bg-violet-400/[0.12]" : "hover:bg-white/[0.04]"}`}
                          onClick={() => setSelectedId(title.media.id)}
                          type="button"
                        >
                          <span
                            aria-label={`${title.media.title} poster`}
                            className="grid size-12 shrink-0 place-items-center overflow-hidden rounded-lg bg-white/[0.04] text-zinc-500"
                            role="img"
                            style={
                              title.media.poster_path
                                ? {
                                    backgroundImage: `url("${title.media.poster_path}")`,
                                    backgroundSize: "cover",
                                    backgroundPosition: "center",
                                  }
                                : undefined
                            }
                          >
                            {!title.media.poster_path && <Icon size={18} />}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-zinc-200">
                              {title.media.title}
                            </span>
                            <span className="mt-1 block truncate text-xs text-zinc-500">
                              {title.media.genres.length > 0
                                ? title.media.genres.join(" · ")
                                : title.media.media_type === "TV"
                                  ? "TV show"
                                  : "Movie"}
                            </span>
                          </span>
                          <span className="shrink-0 text-xs tabular-nums text-zinc-400">
                            {ratingLabel(rating)}/10
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>

          {selectedTitle && (
            <article aria-live="polite" className="panel space-y-5 p-5 xl:sticky xl:top-24">
              <div>
                <p className="eyebrow">
                  {selectedTitle.media.media_type === "TV"
                    ? "YOUR TAKE ON THIS SHOW"
                    : "YOUR TAKE ON THIS FILM"}
                </p>
                <h2 className="mt-2 text-xl font-semibold text-white">
                  {selectedTitle.media.title}
                </h2>
                {selectedTitle.personal_rating !== null && (
                  <div className="mt-3 flex items-center gap-2">
                    <RatingStars rating={selectedTitle.personal_rating} />
                    <span className="text-xs tabular-nums text-amber-200">
                      {ratingLabel(selectedTitle.personal_rating)} / 10
                    </span>
                  </div>
                )}
              </div>

              <FeedbackSection
                icon={<BookOpenText size={16} />}
                label="Your review"
                text={selectedTitle.personal_review}
              />
              <FeedbackSection
                icon={<StickyNote size={16} />}
                label="Your notes"
                text={selectedTitle.personal_notes}
              />
            </article>
          )}
        </div>
      )}
    </section>
  );
}

function RatingStars({ rating }: { rating: number }) {
  return (
    <span aria-hidden="true" className="inline-flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, index) => {
        const threshold = (index + 1) * 2;
        const fill =
          rating >= threshold
            ? "fill-amber-300"
            : rating >= threshold - 1
              ? "fill-amber-300/50"
              : "";
        return (
          <Star
            className={`size-3.5 text-amber-300 ${fill}`}
            key={index}
            strokeWidth={1.7}
          />
        );
      })}
    </span>
  );
}

function FeedbackSection({
  icon,
  label,
  text,
}: {
  icon: ReactNode;
  label: string;
  text: string | null;
}) {
  return (
    <section className="border-t border-white/[0.06] pt-4">
      <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300">
        <span className="text-violet-300">{icon}</span>
        {label}
      </h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-400">
        {text?.trim() || `No ${label.toLowerCase()} saved for this title yet.`}
      </p>
    </section>
  );
}
