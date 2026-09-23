import { InvestigationDashboard } from '@/app/incident/investigation-dashboard';

export default async function IncidentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InvestigationDashboard incidentId={id} />;
}
