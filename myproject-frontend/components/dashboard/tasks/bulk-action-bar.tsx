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
  Loader2
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
import { bulkUpdateTasksAction } from "@/app/actions/productivity";
import { Project, Task } from "@/types/productivity";
import { cn } from "@/lib/utils"

interface BulkActionBarProps {
  selectedIds: number[];
  onClear: () => void;
  projects: Project[];
  className?: string;
}

export function BulkActionBar({ selectedIds, onClear, projects, className }: BulkActionBarProps) {
  const router = useRouter();
  const [isPending, setIsPending] = React.useState(false);

  if (selectedIds.length === 0) return null;

  async function handleBulkUpdate(updates: Partial<Task>) {
    setIsPending(true);
    console.log(updates)
    try {
      // 1. Create the base payload
      const payload: any = {
        ids: selectedIds,
        updates: updates,
      };

      // 2. Only add the key if it exists in this specific update cycle
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
      className ? className : "bottom-6" // Default to bottom-6 if no class provided
    )}>
      <div className="bg-primary text-primary-foreground px-3 py-2 rounded-full shadow-2xl flex items-center gap-2 border border-primary-foreground/20">

        {/* Selection Count */}
        <div className="flex items-center px-2">
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <span className="text-xs font-bold whitespace-nowrap">
              {selectedIds.length} Selected
            </span>
          )}
        </div>

        <div className="h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Action: Status */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full hover:bg-primary-foreground/10"
          onClick={() => handleBulkUpdate({ status: 'completed' })}
          title="Mark as Done"
        >
          <CheckCircle2 className="h-5 w-5" />
        </Button>

        {/* Action: Assigned Date (Schedule) */}
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full hover:bg-primary-foreground/10" title="Schedule">
              <CalendarIcon className="h-5 w-5" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="center" side="top">
            <Calendar
              mode="single"
              onSelect={(date) => {
                if (date) {
                  // Planning is floating: "2024-10-25"
                  handleBulkUpdate({ assigned_date: format(date, "yyyy-MM-dd") });
                }
              }}
            />
          </PopoverContent>
        </Popover>

        {/* Action: Hard Deadline */}
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full hover:bg-primary-foreground/10" title="Set Deadline">
              <Flag className="h-5 w-5" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="center" side="top">
            <Calendar
              mode="single"
              onSelect={(date) => {
                if (date) {
                  // Deadline is absolute. 
                  const endOfDay = new Date(date);
                  endOfDay.setHours(23, 59, 59, 999);
                  handleBulkUpdate({ hard_deadline: endOfDay.toISOString() });
                }
              }}
            />
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

        <div className="h-6 w-px bg-primary-foreground/20 mx-1" />

        {/* Action: Delete */}
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-full hover:bg-destructive hover:text-destructive-foreground text-red-400"
          onClick={() => {
            if (confirm("Delete these tasks?")) {
              // Assuming you'd have a delete action
              // await deleteTasksAction(selectedIds);
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
  );
}
