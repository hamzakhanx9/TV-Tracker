"use client";

import { AlertCircle, Bell, LoaderCircle, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

type Notification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  media_id: string | null;
  episode_id: string | null;
  event_date: string | null;
  created_at: string;
};

type Preferences = {
  release_notifications_enabled: boolean;
  timezone: string;
};

export function NotificationsPanel() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setError("");
    try {
      const [notificationsResponse, preferencesResponse] = await Promise.all([
        fetch("/api/v1/notifications?limit=100", { cache: "no-store", signal }),
        fetch("/api/v1/notification-preferences", { cache: "no-store", signal }),
      ]);
      const [notificationBody, preferencesBody] = await Promise.all([
        notificationsResponse.json().catch(() => null),
        preferencesResponse.json().catch(() => null),
      ]);
      if (!notificationsResponse.ok || !preferencesResponse.ok) {
        const detail = notificationBody?.detail ?? preferencesBody?.detail;
        throw new Error(typeof detail === "string" ? detail : "Could not load notifications.");
      }
      setNotifications(notificationBody as Notification[]);
      window.dispatchEvent(new Event("frame-notifications-updated"));
      setPreferences(preferencesBody as Preferences);
    } catch (loadError) {
      if (loadError instanceof Error && loadError.name === "AbortError") return;
      setError(loadError instanceof Error ? loadError.message : "Could not load notifications.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function clearNotification(id: string) {
    setError("");
    try {
      const response = await fetch(`/api/v1/notifications/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not clear this notification.");
      setNotifications((current) => current.filter((notification) => notification.id !== id));
      window.dispatchEvent(new Event("frame-notifications-updated"));
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "Could not clear notification.");
    }
  }

  async function clearAllNotifications() {
    setError("");
    try {
      const response = await fetch("/api/v1/notifications", { method: "DELETE" });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not clear notifications.",
        );
      }
      setNotifications([]);
      window.dispatchEvent(new Event("frame-notifications-updated"));
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "Could not clear notifications.");
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preferences) return;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const response = await fetch("/api/v1/notification-preferences", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preferences),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof body?.detail === "string" ? body.detail : "Could not save notification preferences.",
        );
      }
      setPreferences(body as Preferences);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save preferences.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-5">
      <header>
        <p className="eyebrow">KEEP YOUR LIBRARY IN SYNC</p>
        <h1 className="mt-2 flex items-center gap-3 text-3xl font-semibold tracking-tight text-white">
          Notifications
          <span className="rounded-full bg-violet-400/10 px-2.5 py-1 text-xs font-medium text-violet-200">
            {notifications.length}
          </span>
        </h1>
      </header>
      {error && (
        <p className="flex items-center gap-2 text-sm text-red-300" role="alert">
          <AlertCircle size={16} />
          {error}
        </p>
      )}

      <form className="panel space-y-4 p-5" onSubmit={savePreferences}>
        <h2 className="text-sm font-medium text-white">Notification preferences</h2>
        {preferences ? (
          <>
            <label className="flex items-center gap-3 text-sm text-zinc-300">
              <input
                checked={preferences.release_notifications_enabled}
                onChange={(event) =>
                  setPreferences({
                    ...preferences,
                    release_notifications_enabled: event.target.checked,
                  })
                }
                type="checkbox"
              />
              New episode announcements and releases for shows you’re watching
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs text-zinc-500" htmlFor="notification-timezone">
                Timezone
              </label>
              <input
                className="h-9 rounded-lg border border-white/[0.08] bg-black/20 px-3 text-sm text-zinc-200"
                id="notification-timezone"
                maxLength={100}
                onChange={(event) =>
                  setPreferences({ ...preferences, timezone: event.target.value })
                }
                value={preferences.timezone}
              />
              <button
                className="rounded-lg bg-violet-400/15 px-3 py-2 text-xs font-medium text-violet-100 hover:bg-violet-400/20 disabled:opacity-50"
                disabled={saving}
                type="submit"
              >
                {saving ? "Saving…" : "Save preferences"}
              </button>
              {saved && <span className="text-xs text-emerald-300">Saved</span>}
            </div>
          </>
        ) : (
          <p className="text-sm text-zinc-500">Preferences are unavailable.</p>
        )}
      </form>

      <div className="space-y-3">
        {!loading && notifications.length > 0 && (
          <div className="flex justify-end">
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-red-400/20 px-3 py-2 text-xs text-red-200 hover:bg-red-400/10"
              onClick={() => void clearAllNotifications()}
              type="button"
            >
              <Trash2 size={14} />
              Clear all
            </button>
          </div>
        )}
        {loading ? (
          <div className="panel flex min-h-32 items-center justify-center gap-3 text-sm text-zinc-400">
            <LoaderCircle className="animate-spin" size={17} />
            Loading notifications…
          </div>
        ) : notifications.length === 0 ? (
          <div className="panel flex min-h-32 flex-col items-center justify-center text-zinc-500">
            <Bell size={20} />
            <p className="mt-3 text-sm">You’re all caught up. New alerts will show here.</p>
          </div>
        ) : (
          notifications.map((notification) => (
            <article
              className="panel flex flex-wrap items-start justify-between gap-4 p-4"
              key={notification.id}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white">{notification.title}</p>
                <p className="mt-1 text-sm leading-6 text-zinc-400">{notification.body}</p>
                <p className="mt-2 text-xs text-zinc-600">
                  {new Intl.DateTimeFormat(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(notification.created_at))}
                </p>
                {notification.media_id && (
                  <Link
                    className="subtle-link mt-2 inline-flex"
                    href={`/media/${notification.media_id}`}
                  >
                    View title
                  </Link>
                )}
              </div>
              <button
                aria-label={`Clear notification: ${notification.title}`}
                className="grid size-9 place-items-center rounded-lg border border-white/[0.08] text-zinc-400 hover:border-red-400/25 hover:bg-red-400/10 hover:text-red-200"
                onClick={() => void clearNotification(notification.id)}
                type="button"
              >
                <Trash2 size={15} />
              </button>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
