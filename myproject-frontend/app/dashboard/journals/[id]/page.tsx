import { getJournalAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import { PageHeader } from "@/components/dashboard/page-header";
import { JournalDetailActions } from "@/components/dashboard/journals/journal-detail-actions";

export default async function JournalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const entry = await getJournalAction(id);

  return (
    <PageContainer variant="prose">
      <PageBody>
        <PageHeader />

        <article className="space-y-8">
          <header className="space-y-2 border-b pb-8">
            <p className="text-sm text-primary font-mono uppercase tracking-widest">
              {entry.entry_type} — {entry.reference_date}
            </p>
            <h1 className="text-4xl font-extrabold tracking-tight">{entry.title || "Untitled Entry"}</h1>
            <div className="pt-4">
              <JournalDetailActions journalId={entry.id.toString()} entryTitle={entry.title || undefined} />
            </div>
          </header>

          <div className="prose prose-slate dark:prose-invert max-w-none lg:prose-lg pb-24">
            <ReactMarkdown>{entry.content}</ReactMarkdown>
          </div>
        </article>
      </PageBody>
    </PageContainer>
  );
}
