# MarkdownText

## Overview

A component for rendering markdown content with full GFM support, LaTeX math, and horizontal code block scrolling. Used for LLM output in chat bubbles and other prose rendering contexts.

## Component Tree

```
MarkdownText
└── <div> (prose wrapper with code block styles)
      └── ReactMarkdown (remark: remarkGfm, remarkMath | rehype: rehypeKatex)
```

## Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `content` | `string \| null \| undefined` | — | Markdown content. `null`/`undefined` are safely handled. |
| `className` | `string` | — | Additional classes on outer wrapper |
| `proseClassName` | `string` | — | Additional prose-specific classes |
| `inverted` | `boolean` | `false` | Uses `prose-invert` for dark backgrounds |

## Internal Operations

**Data Flow**

```
content (string)
    │
    ▼
safeString() ── converts non-string values to string
    │
    ▼
preprocessLaTeX() ── converts \(, \), \[, \] → $, $$, $$ $$
    │
    ▼
ReactMarkdown
    ├── remarkPlugins: [remarkGfm, remarkMath]
    └── rehypePlugins: [rehypeKatex]
    │
    ▼
KaTeX (CSS loaded globally)
```

**safeString**

```typescript
const safeString = (val: any): string => {
  if (typeof val === 'string') return val;
  if (val === null || val === undefined) return '';
  try {
    return JSON.stringify(val, null, 2);
  } catch {
    return String(val);
  }
};
```

Handles unexpected non-string input gracefully.

**LaTeX Pre-processing**

LLMs output `\(inline\)` and `\[block\]` LaTeX delimiters, but `remark-math` only recognizes `$...$` and `$$...$$`. The mismatch exists because markdown treats `\` as an escape character.

```typescript
const preprocessLaTeX = (content: string): string => {
  let result = content.replace(/\\\[/g, '$$$$').replace(/\\\]/g, '$$$$');
  result = result.replace(/\\\(/g, '$').replace(/\\\)/g, '$');
  return result;
};
```

The four-backslash regex (`\\\\(`) is required because JavaScript string literals and regex each consume one layer of backslashes.

**Prose Classes**

```typescript
const proseClass = inverted
  ? 'prose prose-invert max-w-none'
  : 'prose prose-neutral dark:prose-invert max-w-none';
```

**Code Block Scrolling**

Forces horizontal scrolling on code blocks:

```typescript
const codeBlockClass = inverted
  ? 'prose-invert [&_pre]:overflow-x-auto [&_pre]:max-w-full [&_pre]:whitespace-pre'
  : '[&_pre]:overflow-x-auto [&_pre]:max-w-full [&_pre]:whitespace-pre';
```

`[&_pre]:whitespace-pre` prevents wrapping. Use `overflow-x-auto` instead of `whitespace-pre-wrap`.

**KaTeX CSS**

KaTeX CSS must be imported once in `app/globals.css`:

```css
@import "katex/dist/katex.min.css";
```

Without this import, LaTeX renders as raw escaped text.

## Key Files

- `components/ui/markdown-text.tsx`