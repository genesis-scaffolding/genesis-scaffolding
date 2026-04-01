import { getEventAction, getTopicAction } from "@/app/actions/memory";
import { EventLog } from "@/types/memory";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Button } from "@/components/ui/button";
import { Edit3, FileText, Lightbulb } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { PageHeader } from "@/components/dashboard/page-header";

export default async function MemoryDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ type?: string }>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const type = sp.type || "topic";

  let memory;
  try {
    if (type === "event") {
      memory = await getEventAction(id);
    } else {
      memory = await getTopicAction(id);
    }
  } catch (error) {
    notFound();
  }

  const isEvent = type === "event";

  return (
    <PageContainer variant="prose">
      <PageBody>
        <PageHeader />

        <article className="space-y-8">
          <header className="space-y-2 border-b pb-8">
            <div className="flex items-center gap-2 text-sm text-primary font-mono uppercase tracking-widest">
              {isEvent ? (
                <>
                  <FileText className="h-4 w-4" />
                  <span>Event</span>
                </>
              ) : (
                <>
                  <Lightbulb className="h-4 w-4" />
                  <span>Topic</span>
                </>
              )}
              {(memory as EventLog).event_time && (
                <span>— {format(new Date((memory as EventLog).event_time), "yyyy-MM-dd HH:mm")}</span>
              )}
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight">
              {memory.subject || "Untitled Memory"}
            </h1>
            <div className="flex flex-wrap gap-2 pt-4">
              {memory.tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  {tag}
                </Badge>
              ))}
            </div>
            <div className="flex items-center gap-4 pt-4">
              <Badge variant={memory.importance >= 4 ? "default" : "outline"}>
                Importance: {memory.importance}
              </Badge>
              <span className="text-xs text-muted-foreground capitalize">
                {memory.source.replace("_", " ")}
              </span>
              <span className="text-xs text-muted-foreground">
                Created {format(new Date(memory.created_at), "yyyy-MM-dd HH:mm")}
              </span>
            </div>
            <div className="pt-4">
              <Button variant="outline" size="sm" asChild>
                <Link href={`/dashboard/memory/${id}/edit?type=${type}`}>
                  <Edit3 className="mr-2 h-4 w-4" />
                  Edit Memory
                </Link>
              </Button>
            </div>
          </header>

          <div className="prose prose-slate dark:prose-invert max-w-none lg:prose-lg pb-24">
            <ReactMarkdown>{memory.content}</ReactMarkdown>
          </div>
        </article>
      </PageBody>
    </PageContainer>
  );
}
