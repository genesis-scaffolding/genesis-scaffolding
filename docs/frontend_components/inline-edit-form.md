# InlineEditForm

## Overview

A reusable form component for in-place editing of text content. Click to activate a textarea or text input, confirm with keyboard shortcuts or button, and cancel with Esc or the cancel button. The component is only the form layer, it does not manage display vs. edit state.

## Component Tree

```
InlineEditForm
├── (multiline=true) <textarea>
├── (multiline=false) <input type="text">
├── <hint bar> (keyboard shortcut reminder)
└── <Cancel> <Confirm> buttons
```

## Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `value` | `string` | — | Initial content to edit |
| `onConfirm` | `(value: string) => Promise<void>` | — | Called with new value on confirm |
| `onCancel` | `() => void` | — | Called on Escape, Cancel button, or blur |
| `loading` | `boolean` | `false` | Disables input and buttons, shows spinner on Confirm |
| `error` | `string \| null` | `null` | Red border and ring when set |
| `multiline` | `boolean` | `true` | `true` = textarea, `false` = single-line input |
| `minHeight` | `string` | `'200px'` | Minimum height of textarea |
| `className` | `string` | — | Additional CSS classes on the outer container |

## Internal State

| State | Type | Purpose |
|---|---|---|
| `localValue` | `string` | Local copy of `value` for controlled input |

## Internal Operations

**Local Value Sync**

A `useEffect` keeps `localValue` in sync when the `value` prop changes:

```typescript
useEffect(() => {
  setLocalValue(value);
}, [value]);
```

This handles external resets, such as when a parent loads a new record.

**Keyboard Handling**

| Mode | Key | Action |
|---|---|---|
| Multiline | `Ctrl/Cmd+Enter` | Confirm |
| Multiline | `Escape` | Cancel |
| Multiline | `Shift+Enter` | Newline (does not confirm) |
| Single-line | `Enter` | Confirm |
| Single-line | `Escape` | Cancel |

When `loading` is true, keyboard handlers exit early.

**Platform Detection**

The hint bar detects Mac to show the correct modifier key:

```typescript
{navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+Enter to confirm
```

**Error State**

When `error` is set, the input element receives `border-red-500 ring-1 ring-red-500`. The form stays open so the user can retry.

## Key Files

- `components/ui/inline-edit-form.tsx`