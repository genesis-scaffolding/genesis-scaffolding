'use client';

import { useEffect, useState } from 'react';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { ChatProvider } from '@/components/chat/chat-context';
import { ChatWidget } from '@/components/chat/chat-widget';
import { ChatSession, ChatMessage, TokenUsage } from '@/types/chat';
import { openQuickChatAction } from '@/app/actions/quick-chat';
import { Loader2, Maximize2 } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export function QuickChatSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;

    setLoading(true);
    setError(null);
    setSession(null);
    setMessages([]);
    setTokenUsage(undefined);

    openQuickChatAction()
      .then(data => {
        setSession(data.session);
        setMessages(data.messages);
        setTokenUsage(data.context_tokens);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to open chat');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex flex-col p-0" showCloseButton={false}>
        <div className="shrink-0 border-b bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm">
          <div className="py-4 px-4 flex items-center justify-between">
            <div>
              <SheetTitle className="text-lg font-bold tracking-tight">Quick Chat</SheetTitle>
              {session && (
                <p className="text-muted-foreground text-xs tabular-nums">
                  Session #{session.id}
                </p>
              )}
            </div>
            {session && (
              <Link href={`/dashboard/chats/${session.id}`}>
                <Button variant="ghost" size="icon" className="h-7 w-7">
                  <Maximize2 className="h-3.5 w-3.5" />
                </Button>
              </Link>
            )}
          </div>
        </div>

        <div className="flex-1 min-h-0 flex flex-col">
          {loading && (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && !loading && (
            <div className="flex-1 flex items-center justify-center p-4">
              <p className="text-destructive text-sm text-center">{error}</p>
            </div>
          )}

          {!loading && !error && session && (
            <ChatProvider
              session={session}
              initialMessages={messages}
              initialTokenUsage={tokenUsage}
            >
              <ChatWidget showClipboardButton={false} />
            </ChatProvider>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
