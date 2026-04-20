import { AgentForm } from "@/components/dashboard/agent-form";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { PageBody, PageContainer } from "@/components/dashboard/page-container";
import { PageHeader } from "@/components/dashboard/page-header";

export default function NewAgentPage() {
  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <PageHeader>
        </PageHeader>
        <header className="flex items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Create Custom Agent</h1>
            <p className="text-muted-foreground">
              Define a new personality and toolset for your assistant.
            </p>
          </div>
        </header>
        <AgentForm />
      </PageBody>
    </PageContainer>
  );
}
