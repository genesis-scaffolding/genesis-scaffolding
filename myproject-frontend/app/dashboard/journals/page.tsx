import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Button } from "@/components/ui/button";
import { Plus, BookOpen } from "lucide-react";
import Link from "next/link";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getJournalsAction, getProjectsAction } from "@/app/actions/productivity";
import { JournalTable } from "@/components/dashboard/journals/journal-table";
import { JournalCreateDropdown } from "@/components/dashboard/journals/journal-create-dropdown";

export default async function JournalsPage({ searchParams }: { searchParams: Promise<any> }) {
  const sp = await searchParams;
  const type = sp.type || undefined;
  const entries = await getJournalsAction(sp.type ? { entry_type: sp.type } : {});
  const projects = await getProjectsAction();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Journal</h1>
            <p className="text-muted-foreground">Reflect on your progress and plan your future.</p>
          </div>
          <JournalCreateDropdown />
        </div>

        <Tabs defaultValue={type || "all"} className="mb-8">
          <TabsList>
            <TabsTrigger value="all" asChild><Link href="/dashboard/journals">All</Link></TabsTrigger>
            <TabsTrigger value="daily" asChild><Link href="/dashboard/journals?type=daily">Daily</Link></TabsTrigger>
            <TabsTrigger value="weekly" asChild><Link href="/dashboard/journals?type=weekly">Weekly</Link></TabsTrigger>
            <TabsTrigger value="project" asChild><Link href="/dashboard/journals?type=project">Projects</Link></TabsTrigger>
          </TabsList>
        </Tabs>

        {entries.length === 0 ? (
          <div className="text-center py-24 border-2 border-dashed rounded-lg">
            <BookOpen className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">No journal entries found for this category.</p>
          </div>
        ) : (
          <JournalTable entries={entries} projects={projects} />
        )}
      </PageBody>
    </PageContainer>
  );
}
