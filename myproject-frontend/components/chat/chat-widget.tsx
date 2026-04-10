'use client'
import { useState } from 'react';
import { useChat } from "./chat-context";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { TokenBar } from "./token-bar";
import { ClipboardToggleButton } from "./clipboard-icon";
import { ClipboardDrawer } from "./clipboard-drawer";

export function ChatWidget({ showClipboardButton = true }: { showClipboardButton?: boolean }) {
  const { messages, tokenUsage, clipboardMd } = useChat();
  const [isClipboardOpen, setIsClipboardOpen] = useState(false);

  return (
    <div className="flex-1 flex flex-col min-h-0 w-full relative">
      {tokenUsage && (
        <TokenBar
          history={tokenUsage.history_tokens}
          clipboard={tokenUsage.clipboard_tokens}
          total={tokenUsage.total_tokens}
          max={tokenUsage.max_tokens}
          percent={tokenUsage.percent}
        />
      )}
      <MessageList messages={messages} />
      <ChatInput />
      {showClipboardButton && (
        <ClipboardToggleButton
          isOpen={isClipboardOpen}
          onClick={() => setIsClipboardOpen(!isClipboardOpen)}
        />
      )}
      <ClipboardDrawer
        isOpen={isClipboardOpen}
        onClose={() => setIsClipboardOpen(false)}
        clipboardMd={clipboardMd}
      />
    </div>
  );
}
