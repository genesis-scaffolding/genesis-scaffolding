import { getAgentAction, listChatSessionsAction } from "@/app/actions/chat";
import { ChatHistoryTable } from "@/components/dashboard/chat-history-table";
import { StartChatButton } from "@/components/dashboard/start-chat-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Bot, ChevronLeft, Pencil, Wrench, Users, Terminal } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { PageHeader } from "@/components/dashboard/page-header";

interface AgentDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function AgentDetailPage({ params }: AgentDetailPageProps) {
  const { id } = await params;

  // Fetch agent details and all chat sessions in parallel
  const [agent, allSessions] = await Promise.all([
    getAgentAction(id).catch(() => null),
    listChatSessionsAction().catch(() => []),
  ]);

  if (!agent) {
    return notFound();
  }

  // Filter sessions for this specific agent
  const agentSessions = allSessions.filter((s) => s.agent_id === agent.id);

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <PageHeader>
        </PageHeader>
        {/* Navigation & Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Bot className="h-8 w-8 text-blue-600" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">{agent.name}</h1>
                <p className="text-muted-foreground">{agent.description}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0 w-full sm:w-auto justify-end">
            {!agent.read_only && (
              <Button variant="outline" asChild className="shadow-sm">
                <Link href={`/dashboard/agents/${agent.id}/edit`}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit Configuration
                </Link>
              </Button>
            )}
            <div className="shrink-0">
              <StartChatButton agentId={agent.id} agentName={agent.name} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Configuration Details */}
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                  Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Model</label>
                  <div className="mt-1">
                    <Badge variant="secondary" className="text-[10px] font-mono uppercase tracking-wider max-w-[120px] truncate block" title={agent.model_name || "Default System Model"} >
                      {agent.model_name || "Default System Model"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center text-sm">
                    <Wrench className="mr-2 h-4 w-4 text-slate-400" />
                    <span className="font-medium">{agent.allowed_tools.length} Tools Enabled</span>
                  </div>
                  <div className="flex items-center text-sm">
                    <Users className="mr-2 h-4 w-4 text-slate-400" />
                    <span className="font-medium">{agent.allowed_agents.length} Sub-Agents</span>
                  </div>
                  <div className="flex items-center text-sm">
                    <Terminal className="mr-2 h-4 w-4 text-slate-400" />
                    <span className="font-medium">
                      {agent.interactive ? "Interactive Mode" : "Background Only"}
                    </span>
                  </div>
                </div>

                {agent.read_only && (
                  <div className="pt-2">
                    <Badge className="w-full justify-center py-1 bg-slate-100 text-slate-600 hover:bg-slate-100 border-none shadow-none">
                      System Protected Agent
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                  System Prompt
                </CardTitle>
                <CardDescription className="text-xs italic">
                  The core logic governing this agent's behavior.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-50 rounded-md p-4 border text-xs font-mono text-slate-700 max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                  {agent.system_prompt || "No system prompt defined."}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Chat History */}
          <div className="lg:col-span-2 space-y-6 w-full">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold text-slate-900">Recent Activity</h2>
              <p className="text-sm text-muted-foreground">
                History of conversations initiated with {agent.name}.
              </p>
            </div>
            <ChatHistoryTable sessions={agentSessions} />
          </div>
        </div>
      </PageBody>
    </PageContainer>
  );
}
