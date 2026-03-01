'use client'
import React, { useState } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { useChat } from './chat-context';
import { Button } from '@/components/ui/button';
import { ArrowUp, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ChatInput() {
  const { sendMessage, isRunning } = useChat();
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (!input.trim() || isRunning) return;
    sendMessage(input);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Submit on Ctrl+Enter or Cmd+Enter
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
    // Normal 'Enter' now just creates a new line by default in Textarea
  };

  return (
    <div className="w-full">
      <div className="chat-viewport-container py-6">
        <div className={cn(
          "relative flex items-end gap-2 p-3 bg-card border border-muted-foreground/20 rounded-2xl shadow-sm transition-all duration-200",
          "focus-within:border-primary/40 focus-within:ring-[3px] focus-within:ring-primary/5",
          isRunning && "opacity-70 bg-muted/50"
        )}>
          <TextareaAutosize
            autoFocus
            cacheMeasurements
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            className="flex-1 bg-transparent border-none focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 resize-none min-h-[44px] max-h-60 py-2 px-1 text-sm leading-relaxed"
            maxRows={10}
          />

          <div className="flex flex-col justify-end pb-0.5">
            <Button
              onClick={handleSubmit}
              size="icon"
              disabled={!input.trim() || isRunning}
              className={cn(
                "h-9 w-9 rounded-xl transition-all",
                input.trim() ? "bg-primary" : "bg-muted text-muted-foreground"
              )}
            >
              {isRunning ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <ArrowUp className="h-5 w-5" />
              )}
            </Button>
          </div>

          {/* Shortcut Hint */}
          <div className="absolute -bottom-6 right-2 flex gap-3 text-[10px] text-muted-foreground/60 uppercase tracking-widest font-medium">
            <span>{navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'} + Enter to send</span>
          </div>
        </div>
      </div>
    </div>
  );
}
