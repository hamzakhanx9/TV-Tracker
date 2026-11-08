"use client";

import { AlertCircle, Bell, Check, Globe2, LoaderCircle, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { applyTheme, getStoredTheme } from "@/lib/theme";
import type { Theme } from "@/lib/theme";

type Preferences = {
  release_notifications_enabled: boolean;
  timezone: string;
};

export function SettingsPanel() {
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    setTheme(getStoredTheme());
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPreferences() {
      try {
        const response = await fetch("/api/v1/notification-preferences", {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof body?.detail === "string" ? body.detail : "Could not load your settings.",
          );
        }
        setPreferences(body as Preferences);
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        setError(loadError instanceof Error ? loadError.message : "Could not load your settings.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadPreferences();
    return () => controller.abort();
  }, []);

  function chooseTheme(nextTheme: Theme) {
    setTheme(nextTheme);
    applyTheme(nextTheme);
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
          typeof body?.detail === "string" ? body.detail : "Could not save your settings.",
        );
      }
      setPreferences(body as Preferences);
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save your settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <p className="eyebrow">MAKE FRAME YOURS</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Settings</h1>
        <p className="mt-2 text-sm leading-6 text-zinc-400">
          Manage release alerts and the timezone used to schedule them.
        </p>
      </header>

      {error && (
        <p className="flex items-center gap-2 text-sm text-red-300" role="alert">
          <AlertCircle size={16} />
          {error}
        </p>
      )}

      <section aria-labelledby="appearance-heading" className="panel max-w-3xl space-y-5 p-5 sm:p-6">
        <div>
          <h2 className="text-sm font-medium text-white" id="appearance-heading">
            Appearance
          </h2>
          <p className="mt-1 text-xs text-zinc-500">Choose the look that works best for you.</p>
        </div>
        <div aria-label="Theme" className="flex gap-3" role="group">
          {([
            { value: "light", label: "Light", icon: Sun },
            { value: "dark", label: "Dark", icon: Moon },
          ] as const).map(({ value, label, icon: Icon }) => (
            <button
              aria-pressed={theme === value}
              className={`inline-flex h-10 items-center gap-2 rounded-lg border px-4 text-sm transition-colors ${
                theme === value
                  ? "border-violet-400/40 bg-violet-400/10 text-violet-200"
                  : "border-white/[0.08] text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
              }`}
              key={value}
              onClick={() => chooseTheme(value)}
              type="button"
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </section>

      <form className="panel max-w-3xl space-y-6 p-5 sm:p-6" onSubmit={savePreferences}>
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-violet-400/10 text-violet-200">
            <Bell size={18} />
          </span>
          <div>
            <h2 className="text-sm font-medium text-white">Release notifications</h2>
            <p className="mt-1 text-xs text-zinc-500">
              Choose whether FRAME checks for new episode alerts.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-zinc-400" role="status">
            <LoaderCircle className="animate-spin" size={16} />
            Loading settings…
          </div>
        ) : preferences ? (
          <>
            <label className="flex cursor-pointer items-start gap-3 text-sm text-zinc-300">
              <input
                checked={preferences.release_notifications_enabled}
                className="mt-0.5 accent-violet-400"
                onChange={(event) => {
                  setPreferences({
                    ...preferences,
                    release_notifications_enabled: event.target.checked,
                  });
                  setSaved(false);
                }}
                type="checkbox"
              />
              <span>
                New episode announcements and releases
                <span className="mt-1 block text-xs leading-5 text-zinc-500">
                  Alerts are generated for shows in your Currently watching list.
                </span>
              </span>
            </label>

            <div className="border-t border-white/[0.06] pt-5">
              <label
                className="flex items-center gap-2 text-sm font-medium text-zinc-200"
                htmlFor="settings-timezone"
              >
                <Globe2 size={15} className="text-zinc-500" />
                Timezone
              </label>
              <p className="mt-1.5 text-xs leading-5 text-zinc-500">
                Use an IANA timezone, such as America/Los_Angeles or Europe/London.
              </p>
              <input
                autoComplete="off"
                className="mt-3 h-10 w-full max-w-sm rounded-lg border border-white/[0.08] bg-black/20 px-3 text-sm text-zinc-200 outline-none transition-colors focus:border-violet-400/40"
                id="settings-timezone"
                maxLength={100}
                onChange={(event) => {
                  setPreferences({ ...preferences, timezone: event.target.value });
                  setSaved(false);
                }}
                required
                value={preferences.timezone}
              />
            </div>

            <div className="flex items-center gap-3 border-t border-white/[0.06] pt-5">
              <button
                className="rounded-lg bg-violet-400/15 px-4 py-2.5 text-xs font-medium text-violet-100 transition-colors hover:bg-violet-400/20 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={saving}
                type="submit"
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
              {saved && (
                <span
                  className="inline-flex items-center gap-1.5 text-xs text-emerald-300"
                  role="status"
                >
                  <Check size={14} />
                  Changes saved
                </span>
              )}
            </div>
          </>
        ) : (
          <p className="text-sm text-zinc-500">Settings are unavailable.</p>
        )}
      </form>
    </section>
  );
}
