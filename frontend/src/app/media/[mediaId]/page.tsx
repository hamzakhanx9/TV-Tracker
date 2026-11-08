import { MediaDetail } from "@/components/media-detail";

export default async function MediaDetailPage({
  params,
}: {
  params: Promise<{ mediaId: string }>;
}) {
  const { mediaId } = await params;
  return <MediaDetail mediaId={mediaId} />;
}
