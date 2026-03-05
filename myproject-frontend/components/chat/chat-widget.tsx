'use client'
import { useChat } from "./chat-context";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";

export function ChatWidget() {
  const { messages } = useChat();

  return (
    <div className="flex-1 flex flex-col min-h-0 w-full">
      <MessageList messages={messages} />
      <ChatInput />
    </div>
  );
}
