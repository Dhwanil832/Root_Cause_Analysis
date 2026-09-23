import { ReportView } from './report-view';

export default async function ReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ trackId?: string; versionId?: string }>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  return <ReportView incidentId={id} trackId={query.trackId || ''} versionId={query.versionId || ''} />;
}
