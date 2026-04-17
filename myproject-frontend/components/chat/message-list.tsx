'use client'
import React, { useEffect, useRef, useState, memo } from 'react';
import { MessageBubble } from './message-bubble';
import { ChatMessage } from '@/types/chat';
import { Copy, Check, Pencil, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChat } from './chat-context';

export const MessageList = memo(({ messages }: { messages: ChatMessage[] }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolledUpRef = useRef(false);
  const lastMessageCountRef = useRef(messages.length);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [hoveredMessageIndex, setHoveredMessageIndex] = useState<number | null>(null);
  const [tappedMessageIndex, setTappedMessageIndex] = useState<number | null>(null);
  const { sendMessage, isRunning } = useChat();
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      const inputIndex = getInputIndex(editingIndex!, messages);
      setEditingIndex(null);
      sendMessage(editText, inputIndex);
    }
    if (e.key === 'Escape') {
      setEditingIndex(null);
      setEditText('');
    }
  };

  const getInputIndex = (msgIndex: number, messages: ChatMessage[]): number => {
    const userIndices: number[] = [];
    messages.forEach((msg, i) => { if (msg.role === 'user') userIndices.push(i); });
    return userIndices.indexOf(msgIndex) - userIndices.length;
  };

  // Detect if user manually scrolled up (away from bottom)
  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;

    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    // If user scrolled up more than 50px from bottom, mark as scrolled up
    userScrolledUpRef.current = distanceFromBottom > 50;
  };

  // Reset scroll flag when a new user message arrives (new turn)
  useEffect(() => {
    const currentCount = messages.length;
    const prevCount = lastMessageCountRef.current;

    // New message added (user message starts a new turn)
    if (currentCount > prevCount) {
      const lastMessage = messages[messages.length - 1];
      // If the new message is from user, this is a new turn - reset auto-scroll
      if (lastMessage?.role === 'user') {
        userScrolledUpRef.current = false;
      }
    }

    lastMessageCountRef.current = currentCount;
  }, [messages]);

  useEffect(() => {
    if (userScrolledUpRef.current) return;

    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleCopyMarkdown = async (msg: ChatMessage, index: number) => {
    const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2);
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 min-h-0 overflow-y-auto w-full"
    >
      {/* Content wrapper */}
      <div className="chat-viewport-container py-4 space-y-6">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'group relative transition-all duration-200 p-2',
              hoveredMessageIndex === i && 'ring-2 ring-primary/30 rounded-lg'
            )}
            onMouseEnter={() => setHoveredMessageIndex(i)}
            onMouseLeave={() => setHoveredMessageIndex(null)}
            onClick={() => {
              if (hoveredMessageIndex !== i && tappedMessageIndex !== i) {
                setTappedMessageIndex(i);
              }
            }}
          >
            {editingIndex === i ? (
              <div className="flex flex-col gap-2 w-full">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={handleEditKeyDown}
                  className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-md bg-background resize-y"
                  autoFocus
                />
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Ctrl+Enter to confirm</span>
                  <span className="text-muted-foreground/40">|</span>
                  <span>Esc to cancel</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setEditingIndex(null);
                      setEditText('');
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-background border rounded-md text-muted-foreground hover:bg-muted/50"
                  >
                    <X className="w-3.5 h-3.5" />
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      const inputIndex = getInputIndex(i, messages);
                      setEditingIndex(null);
                      await sendMessage(editText, inputIndex);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Confirm
                  </button>
                </div>
              </div>
            ) : (
              <MessageBubble message={msg} />
            )}
            {/* Copy button - appears on hover, positioned at top-right of message */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopyMarkdown(msg, i);
              }}
              className={cn(
                "absolute top-2 right-2 transition-opacity flex items-center gap-1.5 px-2 py-1.5 text-xs bg-background border rounded-md shadow-sm text-muted-foreground hover:text-foreground hover:bg-muted/50",
                (hoveredMessageIndex === i || tappedMessageIndex === i) ? 'opacity-100' : 'opacity-0'
              )}
              title="Copy as Markdown"
            >
              {copiedIndex === i ? (
                <>
                  <Check className="w-3.5 h-3.5 text-green-500" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
            {msg.role === 'user' && !isRunning && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setEditingIndex(i);
                  setEditText(typeof msg.content === 'string' ? msg.content : '');
                }}
                className={cn(
                  "absolute top-2 right-24 transition-opacity flex items-center gap-1.5 px-2 py-1.5 text-xs bg-background border rounded-md shadow-sm text-muted-foreground hover:text-foreground hover:bg-muted/50",
                  (hoveredMessageIndex === i || tappedMessageIndex === i) ? 'opacity-100' : 'opacity-0'
                )}
                title="Edit message"
              >
                <Pencil className="w-3.5 h-3.5" />
                <span>Edit</span>
              </button>
            )}
          </div>
        ))}
        {/* Invisible div for scroll anchoring */}
        <div ref={scrollRef} className="h-4 w-full shrink-0" />
      </div>

    </div>
  );
});

MessageList.displayName = 'MessageList';
