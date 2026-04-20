'use client'
import React, { useState, useEffect } from 'react';
import { X, Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InlineEditFormProps {
  value: string;
  onConfirm: (value: string) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  error?: string | null;
  multiline?: boolean;
  minHeight?: string;
  className?: string;
}

export function InlineEditForm({
  value,
  onConfirm,
  onCancel,
  loading = false,
  error = null,
  multiline = true,
  minHeight = '200px',
  className,
}: InlineEditFormProps) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (loading) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
      return;
    }

    if (multiline) {
      // Multiline: Ctrl+Enter or Cmd+Enter confirms, Shift+Enter adds newline
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        onConfirm(localValue);
        return;
      }
    } else {
      // Single line: Enter confirms, Escape cancels
      if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm(localValue);
        return;
      }
    }
  };

  return (
    <div className={cn('flex flex-col gap-2 w-full', className)}>
      {multiline ? (
        <textarea
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          autoFocus
          style={{ minHeight }}
          className={cn(
            'w-full px-3 py-2 text-sm border rounded-md bg-background resize-y',
            error && 'border-red-500 ring-1 ring-red-500'
          )}
        />
      ) : (
        <input
          type="text"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          autoFocus
          className={cn(
            'w-full px-3 py-2 text-sm border rounded-md bg-background',
            error && 'border-red-500 ring-1 ring-red-500'
          )}
        />
      )}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>
          {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+Enter to confirm
        </span>
        <span className="text-muted-foreground/40">|</span>
        <span>Esc to cancel</span>
      </div>
      <div className="flex gap-2">
        <button
          onClick={onCancel}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-background border rounded-md text-muted-foreground hover:bg-muted/50 disabled:opacity-50"
        >
          <X className="w-3.5 h-3.5" />
          Cancel
        </button>
        <button
          onClick={() => onConfirm(localValue)}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Check className="w-3.5 h-3.5" />
          )}
          Confirm
        </button>
      </div>
    </div>
  );
}