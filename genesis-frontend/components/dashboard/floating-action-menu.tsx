"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus, X, ListTodo, Calendar,
  CalendarRange, StickyNote, Zap, Loader2,
  ChevronRight, MessageSquare
} from "lucide-react";
import { format, startOfWeek } from "date-fns";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { QuickAddTask } from "@/components/dashboard/tasks/quick-add-task";
import { QuickChatSheet } from "@/components/dashboard/quick-chat-sheet";
import { findOrCreateJournalAction } from "@/app/actions/productivity";
import { JournalType } from "@/types/productivity";

type Position = "bottom-right" | "bottom-left" | "top-right" | "top-left";

interface FloatingActionMenuProps {
  position?: Position;
  defaultProjectId?: number;
}

export function FloatingActionMenu({
  position = "bottom-right",
  defaultProjectId
}: FloatingActionMenuProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState<string | null>(null); // Track which journal is loading
  const [activeWidget, setActiveWidget] = useState<"none" | "task">("none");
  const [quickChatOpen, setQuickChatOpen] = useState(false);

  const positionClasses: Record<Position, string> = {
    "bottom-right": "bottom-6 right-6 flex-col-reverse items-end",
    "bottom-left": "bottom-6 left-6 flex-col-reverse items-start",
    "top-right": "top-20 right-6 flex-col items-end",
    "top-left": "top-20 left-6 flex-col items-start",
  };

  const toggleMenu = () => {
    setIsOpen(!isOpen);
    setActiveWidget("none");
  };

  // Helper to handle Journal Creation
  const handleJournalRedirect = async (type: JournalType, dateObj: Date, label: string) => {
    setLoading(label);
    try {
      const refDate = format(dateObj, "yyyy-MM-dd");
      const entry = await findOrCreateJournalAction({
        entry_type: type,
        reference_date: refDate,
        title: `${type.charAt(0).toUpperCase() + type.slice(1)} - ${refDate}`
      });
      router.push(`/dashboard/journals/${entry.id}/edit`);
      setIsOpen(false);
    } catch (error) {
      console.error("Failed to navigate to journal", error);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className={cn("fixed z-50 flex gap-4", positionClasses[position])}>

      {/* 1. MAIN TRIGGER BUTTON */}
      <Button
        size="icon"
        onClick={toggleMenu}
        className={cn(
          "h-14 w-14 rounded-full shadow-2xl transition-all duration-300 border-2 border-background",
          isOpen ? "rotate-45 bg-destructive hover:bg-destructive/90" : "bg-primary shadow-primary/20"
        )}
      >
        <Zap className={cn("h-6 w-6", isOpen ? "text-white" : "fill-current")} />
      </Button>

      {/* 2. THE TRAY */}
      {isOpen && (
        <div className="animate-in fade-in zoom-in-95 slide-in-from-bottom-4 duration-200">
          {activeWidget === "task" ? (

            /* EXPANDED TASK INPUT MODE */
            <div className="bg-background border rounded-2xl shadow-2xl p-3 w-[calc(100vw-48px)] md:w-[600px] lg:w-[700px] flex flex-col gap-2">
              <div className="flex items-center justify-between px-2 pt-1">
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Quick Add Task</span>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setActiveWidget("none")}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="bg-muted/30 rounded-xl p-1">
                <QuickAddTask defaultProjectId={defaultProjectId} showToast={true} />
              </div>
            </div>

          ) : (

            /* ICON TRAY MODE */
            <div className="flex flex-col md:flex-row gap-3 items-center bg-background/90 backdrop-blur-md border p-3 rounded-3xl md:rounded-full shadow-2xl">

              {/* Task Trigger */}
              <TrayIcon
                icon={<ListTodo className="h-5 w-5" />}
                label="Task"
                onClick={() => setActiveWidget("task")}
                variant="primary"
              />

              <div className="w-px h-8 bg-border hidden md:block" />
              <div className="h-px w-8 bg-border md:hidden" />

              {/* Journal: Today */}
              <TrayIcon
                icon={loading === 'today' ? <Loader2 className="animate-spin h-5 w-5" /> : <Calendar className="h-5 w-5" />}
                label="Today's Journal"
                onClick={() => handleJournalRedirect('daily', new Date(), 'today')}
              />

              {/* Journal: This Week */}
              <TrayIcon
                icon={loading === 'weekly' ? <Loader2 className="animate-spin h-5 w-5" /> : <CalendarRange className="h-5 w-5" />}
                label="Weekly Planning"
                onClick={() => handleJournalRedirect('weekly', startOfWeek(new Date(), { weekStartsOn: 1 }), 'weekly')}
              />

              {/* Journal: General/Misc */}
              <TrayIcon
                icon={loading === 'misc' ? <Loader2 className="animate-spin h-5 w-5" /> : <StickyNote className="h-5 w-5" />}
                label="Misc Note"
                onClick={() => handleJournalRedirect('general', new Date(), 'misc')}
              />

              <div className="w-px h-8 bg-border hidden md:block" />

              <TrayIcon
                icon={<MessageSquare className="h-5 w-5" />}
                label="Chat"
                onClick={() => setQuickChatOpen(true)}
              />
            </div>
          )}
        </div>
      )}

      <QuickChatSheet open={quickChatOpen} onOpenChange={setQuickChatOpen} />
    </div>
  );
}

function TrayIcon({
  icon,
  label,
  onClick,
  variant = "ghost"
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: "ghost" | "primary"
}) {
  return (
    <div className="flex flex-col items-center gap-1 group">
      <Button
        variant={variant === "primary" ? "default" : "secondary"}
        size="icon"
        className={cn(
          "h-12 w-12 rounded-full transition-all duration-200",
          variant === "ghost" && "bg-secondary/50 hover:bg-primary hover:text-primary-foreground"
        )}
        onClick={onClick}
      >
        {icon}
      </Button>
      <span className="text-[10px] font-bold uppercase tracking-tighter opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}
