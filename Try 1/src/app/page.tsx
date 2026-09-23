import { getCase, listProviders, listRuns } from "@/lib/server/db";
import { roles } from "@/lib/roles";
import Dashboard from "./ui/dashboard";

export const dynamic = "force-dynamic";

export default function Home() {
  return <Dashboard initialCase={getCase()} providers={listProviders()} runs={listRuns()} roles={[...roles]} />;
}
