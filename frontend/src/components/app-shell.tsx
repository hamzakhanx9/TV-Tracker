"use client";

import {
  Activity,
  CalendarDays,
  Clapperboard,
  Film,
  LayoutDashboard,
  Menu,
  Search,
  Settings2,
  Sparkles,
  Tv2,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const primaryNavigation = [
  { label: "Home", href: "/", icon: LayoutDashboard },
  { label: "Discover", href: "/discover", icon: Search },
  { label: "Movies", href: "/movies", icon: Film },
  { label: "TV shows", href: "/tv", icon: Tv2 },
  { label: "Calendar", href: "/calendar", icon: CalendarDays },
];

const personalNavigation = [
  { label: "Watchlist", href: "/watchlist", icon: Clapperboard },
  { label: "For you", href: "/recommendations", icon: Sparkles },
  { label: "Your stats", href: "/statistics", icon: Activity },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-[248px] flex-col border-r border-white/[0.06] bg-[#0c0c0f] px-4 py-5 transition-transform duration-200 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-2">
          <Link className="flex items-center gap-3" href="/" onClick={() => setMobileOpen(false)}>
            <span className="grid size-9 place-items-center rounded-xl bg-violet-400/10 text-violet-300">
              <Clapperboard size={19} strokeWidth={1.7} />
            </span>
            <span className="text-sm font-bold tracking-[0.23em] text-zinc-100">FRAME</span>
          </Link>
          <button
            aria-label="Close navigation"
            className="grid size-8 place-items-center rounded-lg text-zinc-500 hover:bg-white/[0.05] hover:text-white lg:hidden"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-9 px-2">
          <p className="eyebrow">YOUR SPACE</p>
          <nav aria-label="Main navigation" className="mt-3 space-y-1">
            {primaryNavigation.map((item) => (
              <NavItem
                key={item.href}
                {...item}
                active={pathname === item.href}
                onNavigate={() => setMobileOpen(false)}
              />
            ))}
          </nav>
        </div>

        <div className="mt-8 px-2">
          <p className="eyebrow">YOUR LIBRARY</p>
          <nav aria-label="Personal library" className="mt-3 space-y-1">
            {personalNavigation.map((item) => (
              <NavItem
                key={item.href}
                {...item}
                active={pathname === item.href}
                onNavigate={() => setMobileOpen(false)}
              />
            ))}
          </nav>
        </div>

        <div className="mt-auto">
          <div className="mx-1 mb-4 rounded-xl border border-white/[0.06] bg-white/[0.025] p-3.5">
            <p className="text-xs font-medium text-zinc-300">A quieter kind of queue</p>
            <p className="mt-1.5 text-[11px] leading-5 text-zinc-500">
              One home for every story on your list.
            </p>
          </div>
          <NavItem
            label="Settings"
            href="/settings"
            icon={Settings2}
            active={pathname === "/settings"}
            onNavigate={() => setMobileOpen(false)}
          />
          <div className="mt-4 border-t border-white/[0.06] px-2 pt-4 text-[10px] tracking-wide text-zinc-600">
            FRAME · FOUNDATION
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-10 border-b border-white/[0.055] bg-[#09090b]/85 backdrop-blur-xl">
          <div className="flex h-[68px] items-center justify-between gap-4 px-5 sm:px-8">
            <button
              aria-label="Open navigation"
              className="grid size-9 place-items-center rounded-lg border border-white/[0.07] text-zinc-400 hover:bg-white/[0.05] lg:hidden"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={18} />
            </button>
            <div className="hidden text-xs text-zinc-500 sm:block">
              A little more in tune with what you watch.
            </div>
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/[0.07] bg-white/[0.025] px-3 text-xs text-zinc-400 transition-colors hover:border-white/[0.12] hover:text-zinc-200"
              href="/discover"
            >
              <Search size={14} />
              <span>Find something to watch</span>
              <span className="ml-3 hidden rounded border border-white/[0.08] px-1.5 py-0.5 text-[10px] text-zinc-600 md:inline">
                ⌘ K
              </span>
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-10">{children}</main>
      </div>
    </div>
  );
}

function NavItem({
  label,
  href,
  icon: Icon,
  active,
  onNavigate,
}: {
  label: string;
  href: string;
  icon: LucideIcon;
  active: boolean;
  onNavigate: () => void;
}) {
  return (
    <Link
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-10 items-center gap-3 rounded-lg px-3 text-[13px] transition-colors",
        active
          ? "bg-violet-400/[0.11] font-medium text-violet-200"
          : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200",
      )}
      href={href}
      onClick={onNavigate}
    >
      <Icon size={16} strokeWidth={1.7} />
      {label}
    </Link>
  );
}
