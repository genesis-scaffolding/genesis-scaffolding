'use client'
import { useChat } from "./chat-context";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { TokenBar } from "./token-bar";

export function ChatWidget() {
  const { messages, tokenUsage } = useChat();

  return (
    <div className="flex-1 flex flex-col min-h-0 w-full">
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
    </div>
  );
}
