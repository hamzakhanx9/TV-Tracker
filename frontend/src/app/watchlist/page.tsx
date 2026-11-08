import { MediaLibrary } from "@/components/media-library";

export default function WatchlistPage() {
  return (
    <MediaLibrary
      initialFilter={["PLAN_TO_WATCH", "ON_HOLD", "DROPPED"]}
      mediaType="ALL"
      showStatusFilter={false}
      title="Watchlist"
    />
  );
}
