import { AgentForm } from "@/components/dashboard/agent-form";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";

export default function NewAgentPage() {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/chats">
            <ChevronLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Custom Agent</h1>
          <p className="text-muted-foreground">
            Define a new personality and toolset for your assistant.
          </p>
        </div>
      </header>

      <AgentForm />
    </div>
  );
}
