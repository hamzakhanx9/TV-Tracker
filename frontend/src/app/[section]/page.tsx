import { notFound } from "next/navigation";
import { CalendarView } from "@/components/calendar-view";

const sections: Record<string, { title: string; description: string }> = {
  discover: {
    title: "Discover",
    description: "Search and explore movies and shows from your connected metadata providers.",
  },
  movies: {
    title: "Movies",
    description: "Your film collection, watch history, and personal ratings will live here.",
  },
  tv: {
    title: "TV shows",
    description: "Follow your series and keep every season and episode in sync.",
  },
  calendar: {
    title: "Release calendar",
    description: "Keep track of upcoming episodes, premieres, and movie releases.",
  },
  watchlist: {
    title: "Watchlist",
    description: "Save the titles you want to get to next.",
  },
  recommendations: {
    title: "For you",
    description: "Thoughtful picks shaped by your taste and viewing history.",
  },
  statistics: {
    title: "Your stats",
    description: "A closer look at your viewing habits, milestones, and favorites.",
  },
  settings: {
    title: "Settings",
    description: "Personalize FRAME and manage your account preferences.",
  },
};

export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  const content = sections[section];
  if (!content) notFound();
  if (section === "calendar") return <CalendarView />;

  return (
    <section className="panel flex min-h-[420px] flex-col items-center justify-center px-6 text-center">
      <p className="eyebrow">FRAME / {content.title.toUpperCase()}</p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">{content.title}</h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-zinc-400">{content.description}</p>
      <p className="mt-8 rounded-full border border-white/[0.07] bg-white/[0.025] px-4 py-2 text-xs text-zinc-500">
        This feature is planned for a future implementation stage.
      </p>
    </section>
  );
}
