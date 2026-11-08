"use client";

import { AlertCircle, CalendarDays, ChevronLeft, ChevronRight, Clock3 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type CalendarEvent = {
  id: string;
  media_id: string;
  media_type: "MOVIE" | "TV";
  title: string;
  episode_title: string | null;
  overview: string | null;
  event_type: "MOVIE_RELEASE" | "EPISODE_AIRING";
  event_date: string;
  starts_at: string | null;
  season_number: number | null;
  episode_number: number | null;
  watched: boolean;
};

type CalendarResponse = {
  start: string;
  end: string;
  timezone: string;
  events: CalendarEvent[];
};

const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function dateKey(date: Date) {
  return [
    date.getUTCFullYear(),
    String(date.getUTCMonth() + 1).padStart(2, "0"),
    String(date.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function monthStart(date: Date) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
}

function shiftMonth(date: Date, amount: number) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + amount, 1));
}

export function CalendarView() {
  const [month, setMonth] = useState(() => monthStart(new Date()));
  const [timezone, setTimezone] = useState("");
  const [calendar, setCalendar] = useState<CalendarResponse | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  }, []);

  useEffect(() => {
    if (!timezone) return;
    const start = monthStart(month);
    const end = new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth() + 1, 0));
    const params = new URLSearchParams({
      start: dateKey(start),
      end: dateKey(end),
      timezone,
    });
    const controller = new AbortController();

    async function loadCalendar() {
      setLoading(true);
      setError("");
      setCalendar(null);
      setSelectedEvent(null);
      try {
        const response = await fetch(`/api/v1/calendar?${params}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not load the calendar.",
          );
        }
        setCalendar(body as CalendarResponse);
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "Could not load the calendar.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadCalendar();
    return () => controller.abort();
  }, [month, timezone]);

  const eventsByDate = useMemo(() => {
    const grouped = new Map<string, CalendarEvent[]>();
    for (const event of calendar?.events ?? []) {
      const current = grouped.get(event.event_date) ?? [];
      current.push(event);
      grouped.set(event.event_date, current);
    }
    return grouped;
  }, [calendar]);

  const cells = useMemo(() => {
    const first = monthStart(month);
    const firstVisible = new Date(
      Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), 1 - first.getUTCDay()),
    );
    return Array.from({ length: 42 }, (_, index) =>
      new Date(
        Date.UTC(
          firstVisible.getUTCFullYear(),
          firstVisible.getUTCMonth(),
          firstVisible.getUTCDate() + index,
        ),
      ),
    );
  }, [month]);

  const monthLabel = new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(month);

  function formatEventTime(event: CalendarEvent) {
    if (!event.starts_at) return "All day";
    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
      timeZone: timezone,
    }).format(new Date(event.starts_at));
  }

  return (
    <section className="space-y-5">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">YOUR LIBRARY, ON THE HORIZON</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Release calendar</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Upcoming and past movie releases and episodes for titles in your library.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            aria-label="Previous month"
            className="grid size-10 place-items-center rounded-lg border border-white/[0.08] text-zinc-300 hover:bg-white/[0.05]"
            onClick={() => setMonth((current) => shiftMonth(current, -1))}
            type="button"
          >
            <ChevronLeft size={17} />
          </button>
          <h2 aria-live="polite" className="min-w-36 text-center text-sm font-medium text-white">
            {monthLabel}
          </h2>
          <button
            aria-label="Next month"
            className="grid size-10 place-items-center rounded-lg border border-white/[0.08] text-zinc-300 hover:bg-white/[0.05]"
            onClick={() => setMonth((current) => shiftMonth(current, 1))}
            type="button"
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </header>

      {error && (
        <p aria-live="polite" className="flex items-center gap-2 text-sm text-red-300" role="alert">
          <AlertCircle size={16} />
          {error}
        </p>
      )}

      <div className="panel overflow-x-auto p-3 sm:p-5">
        <div aria-busy={loading} className="min-w-[700px]">
          <div className="grid grid-cols-7 border-b border-white/[0.07] pb-2">
            {weekdays.map((day) => (
              <p className="px-2 py-1 text-center text-xs font-medium text-zinc-500" key={day}>
                {day}
              </p>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((cell) => {
              const key = dateKey(cell);
              const inMonth = cell.getUTCMonth() === month.getUTCMonth();
              const dayEvents = eventsByDate.get(key) ?? [];
              return (
                <div
                  className={`min-h-28 border-b border-r border-white/[0.055] p-1.5 sm:min-h-32 sm:p-2 ${
                    inMonth ? "" : "bg-black/10"
                  }`}
                  key={key}
                >
                  <p className={`mb-1.5 text-xs ${inMonth ? "text-zinc-300" : "text-zinc-700"}`}>
                    {cell.getUTCDate()}
                  </p>
                  <div className="space-y-1">
                    {dayEvents.slice(0, 3).map((event) => (
                      <button
                        aria-label={`${event.title}, ${formatEventTime(event)}`}
                        className={`block w-full truncate rounded px-1.5 py-1 text-left text-[10px] leading-4 sm:text-xs ${
                          event.event_type === "MOVIE_RELEASE"
                            ? "bg-amber-400/10 text-amber-200 hover:bg-amber-400/20"
                            : "bg-violet-400/10 text-violet-200 hover:bg-violet-400/20"
                        } ${event.watched ? "opacity-55" : ""}`}
                        key={event.id}
                        onClick={() => setSelectedEvent(event)}
                        title={event.title}
                        type="button"
                      >
                        {event.media_type === "TV" ? "" : "FILM "}
                        {event.title}
                      </button>
                    ))}
                    {dayEvents.length > 3 && (
                      <p className="px-1 text-[10px] text-zinc-500">+{dayEvents.length - 3} more</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {selectedEvent && (
        <section aria-live="polite" className="panel min-h-28 p-5">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <p className="eyebrow">
                {selectedEvent.event_type === "MOVIE_RELEASE" ? "MOVIE RELEASE" : "EPISODE AIRING"}
              </p>
              <h2 className="mt-1 text-base font-medium text-white">{selectedEvent.title}</h2>
              {selectedEvent.media_type === "TV" && (
                <p className="mt-1 text-xs text-zinc-400">
                  {selectedEvent.episode_title ?? "Episode title unavailable"}
                </p>
              )}
              {selectedEvent.overview && (
                <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
                  {selectedEvent.overview}
                </p>
              )}
              <Link
                className="subtle-link mt-2 inline-flex"
                href={`/media/${selectedEvent.media_id}`}
              >
                View title
              </Link>
            </div>
            <div className="flex items-center gap-2 text-sm text-zinc-300">
              <CalendarDays size={15} className="text-zinc-500" />
              <time dateTime={selectedEvent.event_date}>
                {new Intl.DateTimeFormat(undefined, {
                  dateStyle: "long",
                  timeZone: "UTC",
                }).format(new Date(`${selectedEvent.event_date}T12:00:00Z`))}
              </time>
              <Clock3 size={15} className="ml-2 text-zinc-500" />
              {formatEventTime(selectedEvent)}
              {selectedEvent.watched && <span className="ml-1 text-emerald-300">Watched</span>}
            </div>
          </div>
        </section>
      )}

      <p className="text-xs text-zinc-600">Episode times are shown in {timezone || "your local timezone"}.</p>
    </section>
  );
}
