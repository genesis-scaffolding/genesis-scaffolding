'use client'

import { Task } from "@/types/productivity";
import {
  format,
  startOfWeek,
  addDays,
  startOfDay,
  differenceInMinutes,
  parseISO
} from "date-fns";
import { cn } from "@/lib/utils";
import { Clock } from "lucide-react";
import Link from "next/link";


interface CalendarViewProps {
  tasks: Task[];
  selectedDate: Date;
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const HOUR_HEIGHT = 64; // px

export function CalendarView({ tasks, selectedDate }: CalendarViewProps) {
  const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 });
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  // Filter for tasks that have a schedule and belong to this week
  const appointmentTasks = tasks.filter(t => t.scheduled_start);

  return (
    <div className="flex flex-col h-full bg-background border rounded-xl overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 relative scrollbar-gutter-stable no-scrollbar">
        {/* Header: Days of the week */}
        <div className="sticky top-0 z-20 grid grid-cols-[60px_1fr] border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="border-r flex items-center justify-center bg-muted/30">
            <Clock className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="grid grid-cols-7">
            {weekDays.map((day) => (
              <div key={day.toISOString()} className="py-3 text-center border-r last:border-r-0 bg-muted/30">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  {format(day, "eee")}
                </span>
                <p className="text-sm font-bold">{format(day, "d")}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto min-h-0 relative">
          <div className="grid grid-cols-[60px_1fr] min-h-[1536px]"> {/* 24h * 64px */}
            {/* Time Gutter */}
            <div className="border-r bg-muted/10">
              {HOURS.map((hour) => (
                <div key={hour} style={{ height: HOUR_HEIGHT }} className="text-[10px] text-muted-foreground text-right pr-2 pt-1 border-b border-dashed">
                  {format(new Date().setHours(hour, 0), "HH:mm")}
                </div>
              ))}
            </div>

            {/* Grid Columns */}
            <div className="grid grid-cols-7 relative">
              {weekDays.map((day) => (
                <div key={day.toISOString()} className="relative border-r last:border-r-0 border-b-0 h-full">
                  {/* Visual grid lines */}
                  {HOURS.map((h) => (
                    <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b border-dashed opacity-50" />
                  ))}

                  {/* Tasks for this day */}
                  {appointmentTasks
                    .filter(t => format(parseISO(t.scheduled_start!), 'yyyy-MM-dd') === format(day, 'yyyy-MM-dd'))
                    .map(task => {
                      const start = parseISO(task.scheduled_start!);
                      const startMinutes = differenceInMinutes(start, startOfDay(start));
                      const top = (startMinutes / 60) * HOUR_HEIGHT;
                      const height = ((task.duration_minutes || 30) / 60) * HOUR_HEIGHT;

                      return (
                        <Link
                          key={task.id}
                          href={`/dashboard/tasks/${task.id}`} // Link to detail page
                          className={cn(
                            "absolute left-0.5 right-0.5 p-1.5 rounded-md text-[11px] overflow-hidden border shadow-sm z-10 transition-all",
                            "hover:brightness-95 hover:ring-1 hover:ring-primary/30 active:scale-[0.98]", // Hover effects
                            task.status === 'completed' ? "bg-muted text-muted-foreground" : "bg-primary/10 border-primary/20 text-primary"
                          )}
                          style={{ top: `${top}px`, height: `${height}px`, minHeight: '24px' }}
                        >
                          <div className="font-bold truncate leading-tight">{task.title}</div>
                          {height > 35 && (
                            <div className="opacity-70 text-[10px]">{format(start, "HH:mm")}</div>
                          )}
                        </Link>
                      );
                    })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
