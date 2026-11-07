import { Activity, ArrowUpRight, Clapperboard, Film, Tv2 } from "lucide-react";
import type { ReactNode } from "react";
import { BackendStatus } from "@/components/backend-status";

const metrics = [
  { label: "Movies watched", value: "—", icon: Film },
  { label: "Episodes this month", value: "—", icon: Tv2 },
  { label: "Shows to catch up on", value: "—", icon: Activity },
];

export default function DashboardPage() {
  return (
    <div className="space-y-10">
      <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">YOUR SCREEN, IN SYNC</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Good evening.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-zinc-400">
            Your personal space for the stories you watch and the ones still ahead.
          </p>
        </div>
        <BackendStatus />
      </section>

      <section aria-label="Viewing overview" className="grid gap-3 sm:grid-cols-3">
        {metrics.map(({ label, value, icon: Icon }) => (
          <article key={label} className="panel flex items-center justify-between p-5">
            <div>
              <p className="text-sm text-zinc-400">{label}</p>
              <p className="mt-2 text-3xl font-semibold tracking-tight text-zinc-500">{value}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-xl bg-white/[0.04] text-zinc-500">
              <Icon size={18} strokeWidth={1.7} />
            </span>
          </article>
        ))}
      </section>

      <section className="panel relative min-h-[310px] overflow-hidden p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-12 -top-20 size-72 rounded-full bg-violet-500/[0.07] blur-3xl" />
        <div className="relative flex h-full min-h-[250px] flex-col justify-between gap-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">PICK UP WHERE YOU LEFT OFF</p>
              <h2 className="mt-2 text-xl font-medium text-white">Continue watching</h2>
            </div>
            <Clapperboard className="text-zinc-600" size={21} strokeWidth={1.5} />
          </div>
          <div className="mx-auto max-w-md text-center">
            <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-white/[0.07] bg-white/[0.025] text-zinc-500">
              <Tv2 size={23} strokeWidth={1.5} />
            </div>
            <h3 className="mt-4 text-sm font-medium text-zinc-200">Your next episode is waiting</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-500">
              Add a show to your library and your progress will find a home here.
            </p>
            <a className="subtle-link mt-4 inline-flex items-center gap-1.5" href="/tv">
              Explore TV shows <ArrowUpRight size={14} />
            </a>
          </div>
        </div>
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <EmptyPanel
          eyebrow="ON THE HORIZON"
          title="Upcoming releases"
          description="New episodes and film releases will appear here once your library is connected."
          icon={<Tv2 size={18} strokeWidth={1.6} />}
        />
        <EmptyPanel
          eyebrow="CURATED FOR YOU"
          title="A few good picks"
          description="Recommendations will take shape from the genres and titles you enjoy."
          icon={<Film size={18} strokeWidth={1.6} />}
        />
      </section>

      <footer className="pb-2 text-xs text-zinc-600">
        FRAME is just getting started. Your dashboard will fill in as you build your library.
      </footer>
    </div>
  );
}

function EmptyPanel({
  eyebrow,
  title,
  description,
  icon,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: ReactNode;
}) {
  return (
    <article className="panel flex min-h-48 flex-col justify-between p-5">
      <div className="flex items-center justify-between">
        <p className="eyebrow">{eyebrow}</p>
        <span className="text-zinc-600">{icon}</span>
      </div>
      <div>
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">{description}</p>
      </div>
    </article>
  );
}
