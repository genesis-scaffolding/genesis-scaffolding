"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandList, CommandGroup, CommandItem, CommandEmpty } from "@/components/ui/command";
import { updateTaskAction } from "@/app/actions/productivity";
import { Status } from "@/types/productivity";
import { CheckCircle2, Circle, PlayCircle, XCircle, ListTodo, ChevronDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_OPTIONS: { label: string; value: Status; icon: React.ElementType }[] = [
  { label: "Backlog", value: "backlog", icon: ListTodo },
  { label: "Todo", value: "todo", icon: Circle },
  { label: "In Progress", value: "in_progress", icon: PlayCircle },
  { label: "Completed", value: "completed", icon: CheckCircle2 },
  { label: "Canceled", value: "canceled", icon: XCircle },
];

interface TaskStatusBadgeProps {
  taskId: number;
  status: Status;
}

export function TaskStatusBadge({ taskId, status }: TaskStatusBadgeProps) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [isPending, setIsPending] = React.useState(false);

  const currentOption = STATUS_OPTIONS.find((opt) => opt.value === status);
  const Icon = currentOption?.icon || Circle;

  async function handleStatusChange(newStatus: Status) {
    setIsPending(true);
    try {
      await updateTaskAction(taskId, { status: newStatus });
      router.refresh();
      setOpen(false);
    } catch (error) {
      console.error(error);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            "capitalize font-normal cursor-pointer hover:bg-accent",
            status === 'completed' ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 'bg-blue-500/10 text-blue-600 border-blue-500/20'
          )}
        >
          {isPending ? (
            <Loader2 className="h-3 w-3 animate-spin mr-1" />
          ) : (
            <Icon className="h-3 w-3 mr-1" />
          )}
          {status.replace("_", " ")}
          <ChevronDown className="h-3 w-3 ml-1 opacity-50" />
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-[180px]" align="center" side="top" sideOffset={8}>
        <Command>
          <CommandList>
            <CommandEmpty>No status found.</CommandEmpty>
            <CommandGroup>
              {STATUS_OPTIONS.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.value}
                  onSelect={() => handleStatusChange(option.value)}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <option.icon className="h-4 w-4" />
                  {option.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
