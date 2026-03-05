import { getAgentAction } from "@/app/actions/chat";
import { AgentForm } from "@/components/dashboard/agent-form";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

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
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      <header className="space-y-4">
        <Link
          href="/dashboard/agents"
          className="flex items-center text-sm text-muted-foreground hover:text-primary transition-colors"
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back to Registry
        </Link>
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Edit Agent</h1>
          <p className="text-muted-foreground">
            Modify the configuration and instructions for <span className="font-semibold text-foreground">{agent.name}</span>.
          </p>
        </div>
      </header>

      {/* 3. Render the form with the pre-fetched data */}
      <AgentForm initialData={agent} />
    </div>
  );
}
