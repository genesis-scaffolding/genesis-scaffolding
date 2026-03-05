'use client'
import React, { useEffect, useRef, memo } from 'react';
import { MessageBubble } from './message-bubble';
import { ChatMessage } from '@/types/chat';

export const MessageList = memo(({ messages }: { messages: ChatMessage[] }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="flex-1 min-h-0 overflow-y-auto w-full">
      {/* Content wrapper */}
      <div className="chat-viewport-container py-4 space-y-6">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {/* Invisible div for scroll anchoring */}
        <div ref={scrollRef} className="h-4 w-full shrink-0" />
      </div>

    </div>
  );
});
