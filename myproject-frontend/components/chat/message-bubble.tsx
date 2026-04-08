import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Card } from '@/components/ui/card';
import { Loader2, CheckCircle2, Wrench } from 'lucide-react';
import { ChatMessage } from '@/types/chat';
import React, { memo } from 'react';

const safeString = (val: any): string => {
  if (typeof val === 'string') return val;
  if (val === null || val === undefined) return '';
  try {
    return JSON.stringify(val, null, 2);
  } catch {
    return String(val);
  }
};

export const MessageBubble = memo(({ message }: { message: ChatMessage }) => {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-8">
        <div className="bg-[#2f2f2f] text-white px-5 py-3 rounded-[24px] max-w-[85%] shadow-sm
          prose prose-invert max-w-none
          leading-[1.6]
          prose-p:mb-4 prose-p:last:mb-0
          prose-headings:font-semibold prose-headings:text-white
          prose-strong:font-bold prose-strong:text-white
          prose-a:text-blue-300 prose-a:underline">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {safeString(message.content)}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  if (message.role === 'system') {
    return null;
  }

  if (message.role === 'tool') {
    return (
      <div className="flex justify-start mb-4">
        <Card className="bg-muted/50 p-3 max-w-[85%] w-full overflow-hidden">
          <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground font-semibold uppercase">
            <Wrench className="w-3 h-3" />
            Result: {message.name}
          </div>
          <pre className="text-xs font-mono overflow-x-auto p-2 bg-background rounded border">
            {safeString(message.content)}
          </pre>
        </Card>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="flex justify-start mb-10 w-full group">
      <div className="max-w-full w-full space-y-4">

        {/* Reasoning (Keep this subtle) */}
        {message.reasoning_content && (
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="reasoning" className="border-none">
              <AccordionTrigger className="text-[13px] text-muted-foreground/60 py-1 hover:no-underline justify-start gap-2 px-1">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                Thought Process
              </AccordionTrigger>
              <AccordionContent className="pb-4 pt-2 px-4 bg-muted/20 rounded-xl border-l-2 border-blue-500/20">
                <div className="prose prose-sm dark:prose-invert italic text-muted-foreground/80">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.reasoning_content}
                  </ReactMarkdown>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {/* Content: High quality typography */}
        {message.content && (
          <div className="prose prose-neutral dark:prose-invert max-w-none 
            leading-[1.6]
            prose-p:mb-4 prose-p:last:mb-0
            prose-headings:text-foreground prose-headings:font-semibold
            prose-strong:font-bold">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {safeString(message.content)}
            </ReactMarkdown>
          </div>
        )}

        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {message.tool_calls.map((tool, idx) => (
              <div key={idx} className="flex items-center gap-2 text-[11px] bg-background border px-3 py-1 rounded-full shadow-sm">
                {tool.status === 'running' ? (
                  <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                ) : (
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                )}
                <span className="font-mono font-medium">{tool.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}, (prev, next) => {
  // Custom comparison: Only re-render if content, reasoning, or tool status changes
  return (
    prev.message.content === next.message.content &&
    prev.message.reasoning_content === next.message.reasoning_content &&
    prev.message.tool_calls?.length === next.message.tool_calls?.length &&
    prev.message.tool_calls?.[prev.message.tool_calls.length - 1]?.status ===
    next.message.tool_calls?.[next.message.tool_calls.length - 1]?.status
  );
});
