import { getAgentAction } from "@/app/actions/chat";
import { AgentForm } from "@/components/dashboard/agent-form";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { PageHeader } from "@/components/dashboard/page-header";

interface EditAgentPageProps {
  params: Promise<{ id: string }>;
}

export default async function EditAgentPage({ params }: EditAgentPageProps) {
  // 1. Fetch the agent data
  const { id } = await params;
  let agent;
  try {
    agent = await getAgentAction(id);
  } catch (error) {
    return notFound();
  }

  // 2. Security Check: If the agent is read_only, don't allow editing via URL
  if (agent.read_only) {
    redirect('/dashboard/agents');
  }

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <PageHeader />
        <header className="space-y-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight">Edit Agent</h1>
            <p className="text-muted-foreground">
              Modify the configuration and instructions for <span className="font-semibold text-foreground">{agent.name}</span>.
            </p>
          </div>
        </header>

        {/* 3. Render the form with the pre-fetched data */}
        <AgentForm initialData={agent} />
      </PageBody>
    </PageContainer>
  );
}
