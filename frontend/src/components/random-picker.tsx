"use client";

import { ArrowUpRight, Dices, Film, LoaderCircle, Sparkles, Tv2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type MediaKind = "MOVIE" | "TV";
type MediaFilter = "ALL" | MediaKind;
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
    tmdb_rating: number | null;
    genres: string[];
  };
  watch_status: WatchStatus;
};

export function RandomPicker() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mediaFilter, setMediaFilter] = useState<MediaFilter>("ALL");
  const [genreFilter, setGenreFilter] = useState("ALL");
  const [selected, setSelected] = useState<LibraryItem | null>(null);

  const loadLibrary = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/library", { cache: "no-store" });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not load your library.",
        );
      }
      if (!Array.isArray(body)) throw new Error("The library service returned an invalid response.");
      setItems(body as LibraryItem[]);
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : "Could not load your library. Please retry.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLibrary();
  }, [loadLibrary]);

  const watchlistItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.watch_status === "PLAN_TO_WATCH" ||
          item.watch_status === "ON_HOLD" ||
          item.watch_status === "DROPPED",
      ),
    [items],
  );
  const genres = useMemo(
    () =>
      [...new Set(watchlistItems.flatMap((item) => item.media.genres))]
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b)),
    [watchlistItems],
  );
  const candidates = useMemo(
    () =>
      watchlistItems.filter(
        ({ media }) =>
          (mediaFilter === "ALL" || media.media_type === mediaFilter) &&
          (genreFilter === "ALL" || media.genres.includes(genreFilter)),
      ),
    [genreFilter, mediaFilter, watchlistItems],
  );

  function chooseRandom() {
    if (candidates.length === 0) return;
    const options =
      selected && candidates.length > 1
        ? candidates.filter((item) => item.media.id !== selected.media.id)
        : candidates;
    setSelected(options[Math.floor(Math.random() * options.length)]);
  }

  function updateMediaFilter(value: MediaFilter) {
    setMediaFilter(value);
    setSelected(null);
  }

  function updateGenreFilter(value: string) {
    setGenreFilter(value);
    setSelected(null);
  }

  const selectedMedia = selected?.media;
  const selectedYear = (selectedMedia?.release_date || selectedMedia?.first_air_date)?.slice(0, 4);

  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <p className="eyebrow">YOUR NEXT FAVORITE, BY CHANCE</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          The Watch Picker
        </h1>
        <p className="mt-3 text-sm leading-6 text-zinc-400">
          Set the mood, then let titles in your watchlist make the decision for tonight.
        </p>
      </header>

      {error && (
        <p
          aria-live="polite"
          className="rounded-lg border border-red-400/15 bg-red-400/[0.04] px-4 py-3 text-sm text-red-200"
          role="alert"
        >
          {error}
        </p>
      )}

      <section className="panel relative isolate overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-32 -z-10 size-[420px] rounded-full bg-violet-500/[0.11] blur-[100px]"
        />
        <div className="grid gap-8 p-5 sm:p-8 lg:grid-cols-[minmax(240px,0.8fr)_minmax(0,1.2fr)] lg:gap-12 lg:p-10">
          <div className="flex flex-col">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-2xl border border-violet-300/15 bg-violet-400/[0.08] text-violet-200">
                <Dices size={21} strokeWidth={1.6} />
              </span>
              <div>
                <p className="text-sm font-medium text-zinc-100">Tune your pick</p>
                <p className="mt-1 text-xs text-zinc-500">Choose what you feel like watching</p>
              </div>
            </div>

            <fieldset className="mt-8">
              <legend className="text-xs font-medium text-zinc-400">What are we watching?</legend>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {(
                  [
                    ["ALL", "Anything", Sparkles],
                    ["MOVIE", "Movies", Film],
                    ["TV", "TV shows", Tv2],
                  ] as const
                ).map(([value, label, Icon]) => (
                  <button
                    aria-pressed={mediaFilter === value}
                    className={`flex min-h-10 items-center justify-center gap-2 rounded-lg border px-2 text-xs transition-colors ${
                      mediaFilter === value
                        ? "border-violet-300/25 bg-violet-400/[0.11] text-violet-200"
                        : "border-white/[0.07] bg-white/[0.02] text-zinc-400 hover:border-white/[0.13] hover:text-zinc-200"
                    }`}
                    key={value}
                    onClick={() => updateMediaFilter(value)}
                    type="button"
                  >
                    <Icon size={14} />
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>

            <label className="mt-6 block text-xs font-medium text-zinc-400" htmlFor="random-genre">
              Pick a genre
              <select
                className="mt-3 h-11 w-full rounded-lg border border-white/[0.07] bg-[#111114] px-3 text-sm text-zinc-200 outline-none transition-colors focus:border-violet-400/40"
                id="random-genre"
                onChange={(event) => updateGenreFilter(event.target.value)}
                value={genreFilter}
              >
                <option value="ALL">Surprise me with any genre</option>
                {genres.map((genre) => (
                  <option key={genre} value={genre}>
                    {genre}
                  </option>
                ))}
              </select>
            </label>

            <div className="mt-5 flex items-center justify-between gap-3 text-[11px] text-zinc-500">
              <span>
                {loading ? "Finding your titles…" : `${candidates.length} titles match`}
              </span>
              {genreFilter !== "ALL" && <span className="text-violet-300">{genreFilter}</span>}
            </div>

            <button
              className="mt-7 inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-violet-300 px-5 text-sm font-semibold text-[#15131c] shadow-[0_8px_32px_rgb(139_131_246/15%)] transition hover:bg-violet-200 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading || candidates.length === 0}
              onClick={chooseRandom}
              type="button"
            >
              {loading ? (
                <LoaderCircle className="animate-spin" size={17} />
              ) : (
                <Dices size={17} />
              )}
              {selected ? "Roll again" : "Pick for me"}
            </button>
          </div>

          <div
            aria-live="polite"
            className="relative flex min-h-[360px] items-center justify-center overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 sm:min-h-[420px] sm:p-8"
          >
            {selectedMedia ? (
              <article className="relative z-10 grid w-full max-w-xl items-center gap-6 sm:grid-cols-[minmax(140px,0.7fr)_minmax(0,1.3fr)]">
                <div
                  aria-label={`${selectedMedia.title} poster`}
                  className="mx-auto aspect-[2/3] w-full max-w-[210px] overflow-hidden rounded-xl border border-white/[0.08] bg-zinc-900 bg-cover bg-center shadow-2xl shadow-black/40"
                  role="img"
                  style={
                    selectedMedia.poster_path
                      ? { backgroundImage: `url("${selectedMedia.poster_path}")` }
                      : {}
                  }
                >
                  {!selectedMedia.poster_path && (
                    <div className="grid h-full place-items-center text-zinc-700">
                      {selectedMedia.media_type === "MOVIE" ? <Film size={38} /> : <Tv2 size={38} />}
                    </div>
                  )}
                </div>
                <div className="text-center sm:text-left">
                  <p className="eyebrow flex items-center justify-center gap-2 sm:justify-start">
                    <Sparkles size={12} />
                    TONIGHT&apos;S PICK
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold leading-tight tracking-tight text-white sm:text-3xl">
                    {selectedMedia.title}
                  </h2>
                  <p className="mt-2 text-xs text-zinc-400">
                    {selectedMedia.media_type === "TV" ? "TV show" : "Movie"}
                    {selectedYear ? ` · ${selectedYear}` : ""}
                    {selectedMedia.tmdb_rating !== null
                      ? ` · ★ ${selectedMedia.tmdb_rating.toFixed(1)}`
                      : ""}
                  </p>
                  {selectedMedia.genres.length > 0 && (
                    <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
                      {selectedMedia.genres.map((genre) => (
                        <span
                          className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1 text-[10px] text-zinc-300"
                          key={genre}
                        >
                          {genre}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="mt-4 line-clamp-4 text-xs leading-5 text-zinc-400">
                    {selectedMedia.overview || "A little mystery makes movie night more fun."}
                  </p>
                  <Link
                    className="mt-6 inline-flex items-center gap-2 text-xs font-semibold text-violet-300 transition-colors hover:text-violet-200"
                    href={`/media/${selectedMedia.id}`}
                  >
                    View title details
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              </article>
            ) : (
              <div className="max-w-sm text-center">
                <span className="mx-auto grid size-16 place-items-center rounded-2xl border border-white/[0.06] bg-white/[0.025] text-zinc-600">
                  {loading ? (
                    <LoaderCircle className="animate-spin" size={25} />
                  ) : candidates.length === 0 && watchlistItems.length > 0 ? (
                    <Dices size={25} />
                  ) : (
                    <Sparkles size={25} />
                  )}
                </span>
                <h2 className="mt-5 text-lg font-medium text-zinc-200">
                  {loading
                    ? "Shuffling your watchlist"
                    : error
                      ? "Could not load your library"
                      : watchlistItems.length === 0
                        ? "Your watchlist is waiting"
                        : candidates.length === 0
                          ? "No titles match those filters"
                          : "Your next watch is one roll away"}
                </h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  {loading
                    ? "Gathering movies and shows from your watchlist."
                    : error
                      ? "Check your connection and try loading your library again."
                      : watchlistItems.length === 0
                        ? "Add titles to your watchlist by setting them to Plan to watch, On hold, or Dropped, then come back for a surprise."
                        : candidates.length === 0
                          ? "Try another genre or include both movies and TV shows."
                          : "Pick a genre or format, then let chance decide."}
                </p>
                {!loading && error && (
                  <button
                    className="subtle-link mt-5"
                    onClick={() => void loadLibrary()}
                    type="button"
                  >
                    Try again
                  </button>
                )}
                {!loading && !error && watchlistItems.length === 0 && (
                  <div className="mt-5 flex items-center justify-center gap-4">
                    <Link className="subtle-link inline-flex" href="/watchlist">
                      View watchlist
                    </Link>
                    <Link className="subtle-link inline-flex" href="/discover">
                      Discover titles
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
