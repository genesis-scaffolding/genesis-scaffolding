// app/dashboard/chats/history/page.tsx
import { MessageSquare, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { listChatSessionsAction } from '@/app/actions/chat';
import { ChatHistoryTable } from '@/components/dashboard/chat-history/chat-history-table';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';

export default async function ChatHistoryPage() {
  // Fetch sessions on the server
  const sessions = await listChatSessionsAction();

  return (
    <PageContainer variant='dashboard'>
      <PageBody>
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <MessageSquare className="h-8 w-8 text-primary" />
              Chat History
            </h1>
            <p className="text-muted-foreground">
              View and resume your previous conversations with AI agents.
            </p>
          </div>
          <Button asChild variant="default">
            <Link href="/dashboard/chats">
              <Plus className="mr-2 h-4 w-4" />
              New Chat
            </Link>
          </Button>
        </div>

        {/* Table Section */}
        <div className="grid gap-4">
          <ChatHistoryTable sessions={sessions} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
