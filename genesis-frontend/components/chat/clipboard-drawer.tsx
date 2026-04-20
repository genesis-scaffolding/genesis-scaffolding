'use client';

import { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X } from "lucide-react";

interface ClipboardDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  clipboardMd: string | null;
}

export function ClipboardDrawer({ isOpen, onClose, clipboardMd }: ClipboardDrawerProps) {
  // Escape key handler
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <div
        role="dialog"
        aria-modal="true"
        className={`fixed top-0 right-0 h-full w-80 bg-background border-l border-border z-50 transform transition-transform duration-200 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ boxShadow: isOpen ? "-4px 0 20px rgba(0,0,0,0.1)" : "none" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="font-semibold text-sm">Agent Clipboard</h3>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-6 h-6 rounded hover:bg-accent transition-colors"
            aria-label="Close clipboard"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-57px)] p-4">
          {clipboardMd ? (
            <div className="prose prose-sm dark:prose-invert max-w-none leading-[1.5]">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{clipboardMd}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No clipboard content yet.</p>
          )}
        </div>
      </div>
    </>
  );
}
