import { getAgentsAction } from '@/app/actions/chat';
import { AgentCard } from '@/components/dashboard/agent-card';
import { Button } from '@/components/ui/button';
import { Plus, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';

export default async function AgentsPage() {
  const allAgents = await getAgentsAction();
  const interactiveAgents = allAgents.filter((agent) => agent.interactive);

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        {/* Header Section */}
        <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-blue-500" />
              <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                Agent Registry
              </h1>
            </div>
            <p className="text-lg text-muted-foreground">
              Select an agent or create a custom one to suit your workflow.
            </p>
          </div>

          <Button asChild size="lg" className="shadow-sm">
            <Link href="/dashboard/agents/new">
              <Plus className="mr-2 h-5 w-5" />
              Create Agent
            </Link>
          </Button>
        </header>

        {/* Grid Section */}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            href="/dashboard/agents/new"
            className="group flex flex-col items-center justify-center space-y-3 rounded-xl border-2 border-dashed border-slate-200 p-6 transition-colors hover:border-blue-400 hover:bg-blue-50/50 dark:border-slate-800 dark:hover:bg-blue-950/20"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 group-hover:bg-blue-100 transition-colors dark:bg-slate-800">
              <Plus className="h-6 w-6 text-slate-600 group-hover:text-blue-600 dark:text-slate-400" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-slate-900 dark:text-white">New Agent</p>
              <p className="text-sm text-muted-foreground">Define custom logic</p>
            </div>
          </Link>

          {interactiveAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>

        {/* Empty State */}
        {interactiveAgents.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 border rounded-xl bg-slate-50/50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-800">
            <p className="text-muted-foreground font-medium">No agents found</p>
            <p className="text-sm text-muted-foreground/70">
              Create your first agent to get started.
            </p>
          </div>
        )}
      </PageBody>
    </PageContainer>
  );
}
