'use client';

import { ChevronLeft } from "lucide-react";

interface ClipboardToggleButtonProps {
  isOpen: boolean;
  onClick: () => void;
}

export function ClipboardToggleButton({ isOpen, onClick }: ClipboardToggleButtonProps) {
  return (
    <button
      onClick={onClick}
      className="absolute top-1/2 -translate-y-1/2 z-10 flex items-center justify-center w-6 h-12 rounded-l-md bg-background border border-r-0 border-border shadow-sm hover:bg-accent transition-colors"
      style={{ right: 0 }}
      title={isOpen ? "Close clipboard" : "Open clipboard"}
      aria-label={isOpen ? "Close clipboard" : "Open clipboard"}
      aria-expanded={isOpen}
    >
      <ChevronLeft
        className={`w-4 h-4 transition-transform duration-200 ${isOpen ? "rotate-0" : "rotate-180"}`}
      />
    </button>
  );
}
