'use client'

import { Task } from "@/types/productivity";
import {
  format,
  startOfWeek,
  addDays,
  startOfDay,
  differenceInMinutes,
  parseISO,
  isToday,
  isSameDay
} from "date-fns";
import { cn } from "@/lib/utils";
import { Clock, AlertCircle } from "lucide-react";
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

  // Filter for tasks that have a scheduled start (Appointments)
  const appointmentTasks = tasks.filter(t => t.scheduled_start);

  // Filter for tasks with hard deadlines
  const deadlineTasks = tasks.filter(t => t.hard_deadline);

  return (
    <div className="flex flex-col h-full bg-background border rounded-xl overflow-hidden min-w-[700px]">
      <div className="flex-1 overflow-y-auto min-h-0 relative scrollbar-gutter-stable no-scrollbar">

        {/* Header: Days of the week */}
        <div className="sticky top-0 z-30 grid grid-cols-[60px_1fr] border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="border-r flex items-center justify-center bg-muted/30">
            <Clock className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="grid grid-cols-7">
            {weekDays.map((day) => {
              const today = isToday(day);

              // Find generic deadlines for this day (23:59)
              const genericDeadlines = deadlineTasks.filter(t => {
                const d = parseISO(t.hard_deadline!);
                return isSameDay(d, day) && format(d, 'HH:mm') === '23:59';
              });

              return (
                <div key={day.toISOString()} className={cn(
                  "flex flex-col border-r last:border-r-0 min-h-[80px]",
                  today ? "bg-primary/[0.05]" : "bg-muted/30"
                )}>
                  <div className="py-3 text-center">
                    <span className={cn(
                      "text-xs font-medium uppercase",
                      today ? "text-primary" : "text-muted-foreground"
                    )}>
                      {format(day, "eee")}
                    </span>
                    <p className={cn("text-sm font-bold", today && "text-primary")}>
                      {format(day, "d")}
                    </p>
                  </div>

                  {/* Generic Deadlines Area (Top of the day) */}
                  <div className="px-1 pb-1 space-y-1">
                    {genericDeadlines.map(task => (
                      <Link
                        key={`generic-${task.id}`}
                        href={`/dashboard/tasks/${task.id}`}
                        className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-red-100 border border-red-200 text-red-700 font-medium hover:bg-red-200 transition-colors truncate"
                        title={`Deadline: ${task.title}`}
                      >
                        <AlertCircle className="w-3 h-3 shrink-0" />
                        <span className="truncate">{task.title}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto min-h-0 relative">
          <div className="grid grid-cols-[60px_1fr] min-h-[1536px]">
            {/* Time Gutter */}
            <div className="border-r bg-muted/10">
              {HOURS.map((hour) => (
                <div key={hour} style={{ height: HOUR_HEIGHT }} className="text-[10px] text-muted-foreground text-right pr-2 pt-1 border-b border-dashed">
                  {format(new Date().setHours(hour, 0), "HH:mm")}
                </div>
              ))}
            </div>

            {/* Grid Columns */}
            <div className="overflow-x-auto">
              <div className="grid grid-cols-7 relative">
                {weekDays.map((day) => {
                  const today = isToday(day);

                  return (
                    <div key={day.toISOString()} className={cn(
                      "relative border-r last:border-r-0 border-b-0 h-full",
                      today && "bg-primary/[0.02]"
                    )}>
                      {/* Visual grid lines */}
                      {HOURS.map((h) => (
                        <div key={h} style={{ height: HOUR_HEIGHT }} className="border-b border-dashed opacity-50" />
                      ))}

                      {/* 1. Render Appointment Tasks */}
                      {appointmentTasks
                        .filter(t => isSameDay(parseISO(t.scheduled_start!), day))
                        .map(task => {
                          const start = parseISO(task.scheduled_start!);
                          const startMinutes = differenceInMinutes(start, startOfDay(start));
                          const top = (startMinutes / 60) * HOUR_HEIGHT;
                          const height = ((task.duration_minutes || 30) / 60) * HOUR_HEIGHT;

                          return (
                            <Link
                              key={`appointment-${task.id}`}
                              href={`/dashboard/tasks/${task.id}`}
                              className={cn(
                                "absolute left-0.5 right-0.5 p-1.5 rounded-md text-[11px] overflow-hidden border shadow-sm z-10 transition-all",
                                "hover:brightness-95 hover:ring-1 hover:ring-primary/30 active:scale-[0.98]",
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

                      {/* 2. Render Specific Real-Time Deadlines */}
                      {deadlineTasks
                        .filter(t => {
                          const d = parseISO(t.hard_deadline!);
                          // Only show in grid if it's the correct day AND NOT the generic 23:59 time
                          return isSameDay(d, day) && format(d, 'HH:mm') !== '23:59';
                        })
                        .map(task => {
                          const deadline = parseISO(task.hard_deadline!);
                          const startMinutes = differenceInMinutes(deadline, startOfDay(deadline));
                          const top = (startMinutes / 60) * HOUR_HEIGHT;

                          return (
                            <Link
                              key={`deadline-${task.id}`}
                              href={`/dashboard/tasks/${task.id}`}
                              className={cn(
                                "absolute left-1 right-1 p-1 rounded border-l-4 z-20 shadow-md transition-all flex flex-col justify-center",
                                "bg-red-50 border-red-500 text-red-900 hover:bg-red-100"
                              )}
                              style={{
                                top: `${top}px`,
                                height: '32px', // Fixed height for deadline markers
                                marginTop: '-16px' // Center the marker on the actual time line
                              }}
                            >
                              <div className="flex items-center gap-1 font-bold text-[10px] truncate">
                                <AlertCircle className="w-3 h-3 shrink-0 text-red-600" />
                                <span className="truncate uppercase">Due: {task.title}</span>
                              </div>
                              <div className="text-[9px] opacity-70 font-medium">
                                {format(deadline, "HH:mm")}
                              </div>
                            </Link>
                          );
                        })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
