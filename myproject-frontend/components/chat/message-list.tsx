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
    <div className="flex-1 overflow-y-auto w-full">
      {/* Centering the content within the scrolling area */}
      <div className="chat-viewport-container py-4 space-y-6">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={scrollRef} className="h-12 w-full" />
      </div>
    </div>
  );
});
