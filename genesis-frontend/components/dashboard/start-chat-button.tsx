'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { MessageSquarePlus, Loader2 } from 'lucide-react';

interface StartChatButtonProps {
  agentId: string;
  agentName: string;
}

export function StartChatButton({ agentId, agentName }: StartChatButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleStartChat = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          title: `Chat with ${agentName}`,
        }),
      });

      if (!response.ok) throw new Error('Failed to create session');

      const session = await response.json();
      // Redirect to the existing chat page
      router.push(`/dashboard/chats/${session.id}`);
    } catch (error) {
      console.error('Error starting chat:', error);
      setIsLoading(false);
      // Optional: Add toast notification here
    }
  };

  return (
    <Button
      onClick={handleStartChat}
      disabled={isLoading}
      className="w-full shadow-sm"
    >
      {isLoading ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <MessageSquarePlus className="mr-2 h-4 w-4" />
      )}
      Start Interaction
    </Button>
  );
}
