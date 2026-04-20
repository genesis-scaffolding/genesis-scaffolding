'use client'

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { cn } from '@/lib/utils';

const safeString = (val: any): string => {
  if (typeof val === 'string') return val;
  if (val === null || val === undefined) return '';
  try {
    return JSON.stringify(val, null, 2);
  } catch {
    return String(val);
  }
};

// Pre-process LaTeX delimiters: \( \) → $ and \[ \] → $$
const preprocessLaTeX = (content: string): string => {
  let result = content.replace(/\\\[/g, '$$$$').replace(/\\\]/g, '$$$$');
  result = result.replace(/\\\(/g, '$').replace(/\\\)/g, '$');
  return result;
};

interface MarkdownTextProps {
  content: string | null | undefined;
  className?: string;
  proseClassName?: string;
  inverted?: boolean; // Use inverted prose for dark backgrounds (like user messages)
}

export function MarkdownText({ content, className, proseClassName, inverted }: MarkdownTextProps) {
  const processed = preprocessLaTeX(safeString(content));
  const proseClass = inverted
    ? 'prose prose-invert max-w-none'
    : 'prose prose-neutral dark:prose-invert max-w-none';

  // Code block styles: scroll horizontally, don't wrap
  const codeBlockClass = inverted
    ? 'prose-invert [&_pre]:overflow-x-auto [&_pre]:max-w-full [&_pre]:whitespace-pre'
    : '[&_pre]:overflow-x-auto [&_pre]:max-w-full [&_pre]:whitespace-pre';

  return (
    <div className={cn(proseClass, codeBlockClass, 'leading-[1.6]', proseClassName, className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}