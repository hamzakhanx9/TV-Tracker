"use client";

import { Activity, ArrowUpRight, Clapperboard, LoaderCircle, Tv2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

type LibraryEntry = {
  media: {
    id: string;
    media_type: "MOVIE" | "TV";
    title: string;
    poster_path: string | null;
  };
  watch_status: "PLAN_TO_WATCH" | "WATCHING" | "COMPLETED" | "ON_HOLD" | "DROPPED";
  watched: boolean;
};

type CatchUpShow = {
  media_id: string;
  title: string;
  unwatched_count: number;
  episodes: {
    title: string;
    season_number: number;
    episode_number: number | null;
  }[];
};

type CalendarEvent = {
  id: string;
  media_type: "MOVIE" | "TV";
  title: string;
  episode_title: string | null;
  event_type: "MOVIE_RELEASE" | "EPISODE_AIRING";
  event_date: string;
};

type DashboardData = {
  library: LibraryEntry[];
  catchUp: CatchUpShow[];
  upcoming: CalendarEvent[];
};

function localDateKey(date: Date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function episodeLabel(season: number, episode: number | null) {
  return `S${String(season).padStart(2, "0")}E${episode === null ? "??" : String(episode).padStart(2, "0")}`;
}

function formatEventDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

export function DashboardPanels() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard() {
      try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        const start = new Date();
        const end = new Date(start);
        end.setDate(end.getDate() + 30);
        const calendarParams = new URLSearchParams({
          start: localDateKey(start),
          end: localDateKey(end),
          timezone,
        });
        const [libraryResponse, catchUpResponse, calendarResponse] = await Promise.all([
          fetch("/api/v1/library", { cache: "no-store", signal: controller.signal }),
          fetch(
            `/api/v1/catch-up?${new URLSearchParams({ timezone })}`,
            { cache: "no-store", signal: controller.signal },
          ),
          fetch(`/api/v1/calendar?${calendarParams}`, {
            cache: "no-store",
            signal: controller.signal,
          }),
        ]);
        const [libraryBody, catchUpBody, calendarBody] = await Promise.all([
          libraryResponse.json().catch(() => null),
          catchUpResponse.json().catch(() => null),
          calendarResponse.json().catch(() => null),
        ]);
        const failedResponse = [
          { response: libraryResponse, body: libraryBody },
          { response: catchUpResponse, body: catchUpBody },
          { response: calendarResponse, body: calendarBody },
        ].find(({ response }) => !response.ok);
        if (failedResponse) {
          throw new Error(
            typeof failedResponse.body?.detail === "string"
              ? failedResponse.body.detail
              : `Could not load your home dashboard (${failedResponse.response.status}).`,
          );
        }
        if (
          !Array.isArray(libraryBody) ||
          !Array.isArray(catchUpBody) ||
          !Array.isArray(calendarBody?.events)
        ) {
          throw new Error("The dashboard service returned invalid data.");
        }
        setData({
          library: libraryBody as LibraryEntry[],
          catchUp: catchUpBody as CatchUpShow[],
          upcoming: calendarBody.events as CalendarEvent[],
        });
        setError("");
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load your home dashboard.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadDashboard();
    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <div
        aria-label="Loading your dashboard"
        className="panel flex min-h-64 items-center justify-center gap-3 text-sm text-zinc-400"
        role="status"
      >
        <LoaderCircle className="animate-spin" size={17} />
        Loading your home…
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="panel p-5 text-sm text-red-300" role="alert">
        {error || "Could not load your home dashboard."}
      </p>
    );
  }

  const watchlistCount = data.library.filter((entry) =>
    ["PLAN_TO_WATCH", "ON_HOLD", "DROPPED"].includes(entry.watch_status),
  ).length;
  const watchingShows = data.library.filter(
    (entry) => entry.media.media_type === "TV" && entry.watch_status === "WATCHING",
  );
  const catchUpByMedia = new Map(data.catchUp.map((show) => [show.media_id, show]));
  const upcoming = data.upcoming.slice(0, 5);

  return (
    <div className="space-y-6">
      <section aria-label="Viewing overview" className="grid gap-3 sm:grid-cols-3">
        <MetricCard
          label="Watchlist titles"
          value={watchlistCount}
          icon={<Clapperboard size={18} />}
        />
        <MetricCard
          label="Currently watching"
          value={watchingShows.length}
          icon={<Tv2 size={18} />}
        />
        <MetricCard
          label="Shows to catch up on"
          value={data.catchUp.length}
          icon={<Activity size={18} />}
        />
      </section>

      <section className="panel relative overflow-hidden p-5 sm:p-7">
        <div className="pointer-events-none absolute -right-12 -top-20 size-72 rounded-full bg-violet-500/[0.07] blur-3xl" />
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">PICK UP WHERE YOU LEFT OFF</p>
              <h2 className="mt-2 text-xl font-medium text-white">Continue watching</h2>
            </div>
            <Clapperboard className="text-zinc-600" size={21} strokeWidth={1.5} />
          </div>
          {watchingShows.length === 0 ? (
            <EmptyState
              description="Set a show to Watching in your TV library and it will appear here."
              href="/tv"
              link="Open TV shows"
            />
          ) : (
            <ul className="mt-5 grid gap-3 sm:grid-cols-2">
              {watchingShows.slice(0, 6).map(({ media }) => {
                const catchUpShow = catchUpByMedia.get(media.id);
                const nextEpisode = catchUpShow?.episodes[0];
                return (
                  <li
                    className="flex min-w-0 items-center gap-3 rounded-xl border border-white/[0.06] bg-black/10 p-3"
                    key={media.id}
                  >
                    {media.poster_path ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        alt=""
                        className="size-12 shrink-0 rounded-lg object-cover"
                        src={media.poster_path}
                      />
                    ) : (
                      <span className="grid size-12 shrink-0 place-items-center rounded-lg bg-white/[0.04] text-zinc-500">
                        <Tv2 size={18} />
                      </span>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-zinc-200">{media.title}</p>
                      <p className="mt-1 truncate text-xs text-zinc-500">
                        {nextEpisode
                          ? `${catchUpShow.unwatched_count} unwatched · ${episodeLabel(nextEpisode.season_number, nextEpisode.episode_number)} ${nextEpisode.title}`
                          : "In your Watching list"}
                      </p>
                    </div>
                    <Link
                      aria-label={`Open ${media.title} in TV shows`}
                      className="grid size-8 shrink-0 place-items-center rounded-lg text-zinc-500 hover:bg-white/[0.06] hover:text-white"
                      href="/tv"
                    >
                      <ArrowUpRight size={15} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">ON THE HORIZON</p>
            <h2 className="mt-2 text-lg font-medium text-white">Upcoming releases</h2>
          </div>
          <Tv2 className="text-zinc-600" size={19} strokeWidth={1.6} />
        </div>
        {upcoming.length === 0 ? (
          <EmptyState
            description="Upcoming movie dates and synced episode airings from your library will show up here."
            href="/calendar"
            link="Open release calendar"
          />
        ) : (
          <ul className="mt-4 divide-y divide-white/[0.06]">
            {upcoming.map((event) => (
              <li className="flex items-center justify-between gap-4 py-3" key={event.id}>
                <div className="min-w-0">
                  <p className="truncate text-sm text-zinc-200">{event.title}</p>
                  {event.episode_title && (
                    <p className="mt-1 truncate text-xs text-zinc-500">{event.episode_title}</p>
                  )}
                </div>
                <span className="shrink-0 text-xs tabular-nums text-zinc-500">
                  {formatEventDate(event.event_date)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function MetricCard({
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

function EmptyState({
  description,
  href,
  link,
}: {
  description: string;
  href: string;
  link: string;
}) {
  return (
    <div className="py-8 text-center">
      <p className="text-sm text-zinc-400">{description}</p>
      <Link className="subtle-link mt-3 inline-flex items-center gap-1.5 text-sm" href={href}>
        {link} <ArrowUpRight size={14} />
      </Link>
    </div>
  );
}
