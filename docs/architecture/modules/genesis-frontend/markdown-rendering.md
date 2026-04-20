# Markdown Rendering

`MarkdownText` component for rendering LLM output with full markdown, code blocks, and LaTeX math support.

## MarkdownText Component

**Path:** `components/ui/markdown-text.tsx`

### Why a Component

LLM output is plain text markdown that may contain code blocks, tables, and LaTeX math. Rendering it correctly requires:

- `react-markdown` — parses markdown into React elements
- `remark-gfm` — GitHub Flavored Markdown (tables, strikethrough, task lists)
- `remark-math` + `rehype-katex` — LaTeX math rendering via KaTeX
- Pre-processing to convert LaTeX delimiters (`\(...\)`, `\[...\]`) to markdown-math delimiters (`$...$`, `$$...$$`)

Bundling this into a single component ensures all message bubbles and other markdown renderers share the same configuration.

### Architecture

```
content (string)
    │
    ▼
safeString() ── converts non-string values to string (JSON.stringify fallback)
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
KaTeX CSS (loaded globally via @import in globals.css)
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `content` | `string \| null \| undefined` | — | The markdown content to render. `null`/`undefined` are safely handled. |
| `className` | `string` | — | Additional classes on the outer wrapper div. |
| `proseClassName` | `string` | — | Additional prose-specific classes (merged into the prose class string). |
| `inverted` | `boolean` | `false` | When `true`, uses `prose-invert` for dark backgrounds (e.g., user message bubbles). |

### Usage

**Basic usage:**

```tsx
import { MarkdownText } from '@/components/ui/markdown-text';

// Renders markdown with light prose style
<MarkdownText content={message.content} />
```

**With dark background (user messages):**

```tsx
<MarkdownText content={message.content} inverted />
```

**With custom prose overrides:**

```tsx
<MarkdownText
  content={message.content}
  proseClassName="prose-p:mb-2 prose-p:last:mb-0"
/>
```

### Code Block Scrolling

The component forces horizontal scrolling on code blocks via Tailwind arbitrary variants:

```tsx
[&_pre]:overflow-x-auto [&_pre]:max-w-full [&_pre]:whitespace-pre
```

This prevents long lines from wrapping or expanding their container. Do **not** use `white-space: pre-wrap` — that wraps instead of scrolling.

### LaTeX Pre-processing

LLMs output `\(inline\)` and `\[block\]` LaTeX delimiters, but `remark-math` only recognizes `$...$` and `$$...$$`. The mismatch exists because markdown treats `\` as an escape character.

The `preprocessLaTeX` function in the component converts delimiters before parsing:

```typescript
const preprocessLaTeX = (content: string): string => {
  let result = content.replace(/\\\\\(/g, '$').replace(/\\\\\)/g, '$');
  result = result.replace(/\\\\\[/g, '$$').replace(/\\\\\]/g, '$$');
  return result;
};
```

The four-backslash regex (`\\\\(`) is required because JavaScript string literals and regex each consume one layer of backslashes.

### KaTeX CSS Requirement

KaTeX CSS must be imported once in `app/globals.css`:

```css
@import "katex/dist/katex.min.css";
```

Without this import, LaTeX renders as raw escaped text.

### Dependencies

The following packages are required in `package.json`:

```json
{
  "katex": "^0.16.0",
  "remark-math": "^6.0.0",
  "rehype-katex": "^7.0.1"
}
```