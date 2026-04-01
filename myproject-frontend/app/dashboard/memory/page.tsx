import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Button } from "@/components/ui/button";
import { Plus, Brain } from "lucide-react";
import Link from "next/link";
import { getMemoriesAction } from "@/app/actions/memory";
import { MemoryTable } from "@/components/dashboard/memory/memory-table";
import { PageHeader } from "@/components/dashboard/page-header";

export default async function MemoryPage() {
  const memories = await getMemoriesAction({ memory_type: "all" });

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Memory</h1>
            <p className="text-muted-foreground">Persistent knowledge and events for the agent.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/dashboard/memory/new?type=event">
                <Plus className="mr-2 h-4 w-4" />
                New Event
              </Link>
            </Button>
            <Button asChild>
              <Link href="/dashboard/memory/new?type=topic">
                <Plus className="mr-2 h-4 w-4" />
                New Topic
              </Link>
            </Button>
          </div>
        </div>

        {memories.events.length === 0 && memories.topics.length === 0 ? (
          <div className="text-center py-24 border-2 border-dashed rounded-lg">
            <Brain className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">No memory entries yet.</p>
            <p className="text-sm text-muted-foreground mt-1">
              Memories are created by the agent or manually.
            </p>
          </div>
        ) : (
          <MemoryTable events={memories.events} topics={memories.topics} />
        )}
      </PageBody>
    </PageContainer>
  );
}
