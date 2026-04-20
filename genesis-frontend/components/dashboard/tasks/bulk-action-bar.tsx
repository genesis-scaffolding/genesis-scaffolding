"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  FolderInput,
  Trash2,
  X,
  Calendar as CalendarIcon,
  Flag,
  Loader2,
  Circle,
  PlayCircle,
  XCircle,
  ListTodo,
  ChevronDown
} from "lucide-react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { bulkUpdateTasksAction, bulkDeleteTasksAction } from "@/app/actions/productivity";
import { Project, Task, Status } from "@/types/productivity"; // Ensure Status is exported from types
import { cn } from "@/lib/utils";

interface BulkActionBarProps {
  selectedIds: number[];
  onClear: () => void;
  projects: Project[];
  className?: string;
}

// Map statuses to labels and icons for the UI
const STATUS_OPTIONS: { label: string; value: Status; icon: any }[] = [
  { label: "Backlog", value: "backlog", icon: ListTodo },
  { label: "Todo", value: "todo", icon: Circle },
  { label: "In Progress", value: "in_progress", icon: PlayCircle },
  { label: "Completed", value: "completed", icon: CheckCircle2 },
  { label: "Canceled", value: "canceled", icon: XCircle },
];

export function BulkActionBar({ selectedIds, onClear, projects, className }: BulkActionBarProps) {
  const router = useRouter();
  const [isPending, setIsPending] = React.useState(false);

  if (selectedIds.length === 0) return null;

  async function handleBulkUpdate(updates: Partial<Task>) {
    setIsPending(true);
    try {
      const payload: any = {
        ids: selectedIds,
        updates: updates,
      };

      if (updates.project_ids !== undefined) {
        payload.set_project_ids = updates.project_ids;
      }

      await bulkUpdateTasksAction(payload);
      onClear();
      router.refresh();
    } catch (error) {
      console.error(error);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className={cn(
      "fixed left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4",
      className ? className : "bottom-6"
    )}>
      <div className="bg-primary text-primary-foreground px-3 py-3 md:py-2 rounded-3xl md:rounded-full shadow-2xl flex flex-col md:flex-row items-stretch md:items-center gap-2 md:gap-0 border border-primary-foreground/20">

        {/* Row 1/Col 1: Selection count */}
        <div className="flex items-center justify-center px-2 py-1 md:py-0">
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <span className="text-xs font-bold whitespace-nowrap">
              {selectedIds.length} Selected
            </span>
          )}
        </div>

        {/* Divider: desktop only */}
        <div className="hidden md:block h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Row 2/Col 2: Status dropdown — full width on mobile */}
        <div className="w-full md:w-auto">

        {/* Action: Status Selection */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-9 px-3 rounded-full hover:bg-primary-foreground/10 gap-2 font-medium"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>Status</span>
              <ChevronDown className="h-3 w-3 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="p-0 w-[180px]" align="center" side="top" sideOffset={16}>
            <Command>
              <CommandList>
                <CommandGroup>
                  {STATUS_OPTIONS.map((status) => (
                    <CommandItem
                      key={status.value}
                      onSelect={() => handleBulkUpdate({ status: status.value })}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <status.icon className="h-4 w-4" />
                      {status.label}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
        </div>

        {/* Divider: desktop only */}
        <div className="hidden md:block h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Row 3/Col 3: Remaining action icons */}
        <div className="flex flex-wrap items-center gap-2">

          {/* Action: Assigned Date (Schedule) */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full hover:bg-primary-foreground/10" title="Schedule">
                <CalendarIcon className="h-5 w-5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="center" side="top" sideOffset={16}>
              <div className="flex flex-col">
                <Calendar
                  mode="single"
                  onSelect={(date) => {
                    if (date) {
                      handleBulkUpdate({ assigned_date: format(date, "yyyy-MM-dd") });
                    }
                  }}
                />
                <div className="p-2 border-t border-border">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-center text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => handleBulkUpdate({ assigned_date: null })}
                  >
                    Clear date
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          {/* Action: Hard Deadline */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full hover:bg-primary-foreground/10" title="Set Deadline">
                <Flag className="h-5 w-5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="center" side="top" sideOffset={16}>
              <div className="flex flex-col">
                <Calendar
                  mode="single"
                  onSelect={(date) => {
                    if (date) {
                      const endOfDay = new Date(date);
                      endOfDay.setHours(23, 59, 59, 999);
                      handleBulkUpdate({ hard_deadline: endOfDay.toISOString() });
                    }
                  }}
                />
                <div className="p-2 border-t border-border">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-center text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => handleBulkUpdate({ hard_deadline: null })}
                  >
                    Clear deadline
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          {/* Action: Project Assignment */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full hover:bg-primary-foreground/10" title="Assign Project">
                <FolderInput className="h-5 w-5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="p-0 w-[200px]" align="center" side="top" sideOffset={16}>
              <Command>
                <CommandInput placeholder="Search project..." />
                <CommandList>
                  <CommandEmpty>No project found.</CommandEmpty>
                  <CommandGroup>
                    {projects.map((project) => (
                      <CommandItem
                        key={project.id}
                        onSelect={() => {
                          handleBulkUpdate({ project_ids: [project.id] });
                        }}
                      >
                        {project.name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

        </div>

        {/* Divider: desktop only */}
        <div className="hidden md:block h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Delete + Close actions */}
        <div className="flex items-center gap-2">

        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full hover:bg-destructive hover:text-destructive-foreground text-red-400"
          onClick={() => {
            if (confirm("Delete these tasks?")) {
              bulkDeleteTasksAction(selectedIds)
              onClear();
            }
          }}
        >
          <Trash2 className="h-5 w-5" />
        </Button>

        {/* Close/Deselect */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClear}
          className="h-9 w-9 rounded-full hover:bg-primary-foreground/10"
        >
          <X className="h-5 w-5" />
        </Button>
        </div>
      </div>
    </div>
  );
}
