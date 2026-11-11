import { BackendStatus } from "@/components/backend-status";
import { DashboardPanels } from "@/components/dashboard-panels";

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

      <DashboardPanels />
    </div>
  );
}
