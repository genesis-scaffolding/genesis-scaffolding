export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

import { getChatHistoryAction } from "@/app/actions/chat";
import { notFound } from "next/navigation";
import { ChatProvider } from "@/components/chat/chat-context";
import { ChatWidget } from "@/components/chat/chat-widget";
import { PageContainer } from "@/components/dashboard/page-container";

export default async function ChatDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sessionId = parseInt(id);

  try {
    const data = await getChatHistoryAction(sessionId);
    const initialMessages = data.messages.map((m: any) => m.payload);

    return (
      <ChatProvider session={data.session} initialMessages={initialMessages}>
        <PageContainer variant="app">
          <header className="shrink-0 border-b bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm">
            <div className="chat-viewport-container py-4">
              <h1 className="lg:text-xl text-lg font-bold tracking-tight truncate">
                {data.session.title}
              </h1>
              <p className="text-muted-foreground text-xs tabular-nums">
                Session ID: #{data.session.id}
              </p>
            </div>
          </header>

          <ChatWidget />
        </PageContainer>
      </ChatProvider>
    );
  } catch (error) {
    notFound();
  }
}
