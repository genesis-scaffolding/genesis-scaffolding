// app/dashboard/calendar/page.tsx
'use client'

import { useEffect, useState } from "react";
import { PageContainer } from "@/components/dashboard/page-container";
import { CalendarView } from "@/components/dashboard/calendar/calendar-view";
import { CalendarNav } from "@/components/dashboard/calendar/calendar-nav";
import { getTasksAction } from "@/app/actions/productivity";
import { Task } from "@/types/productivity";
import { startOfWeek, endOfWeek, format } from "date-fns";

export default function CalendarPage() {
  const [date, setDate] = useState<Date>(new Date());
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTasks() {
      setLoading(true);
      try {
        // Fetching range of tasks for the current week
        const start = format(startOfWeek(date), 'yyyy-MM-dd');
        const end = format(endOfWeek(date), 'yyyy-MM-dd');

        // Using your server action with search params
        const data = await getTasksAction({
          scheduled_after: start,
          scheduled_before: end
        });
        setTasks(data);
      } catch (error) {
        console.error("Failed to load tasks", error);
      } finally {
        setLoading(false);
      }
    }
    loadTasks();
  }, [date]);

  return (
    <PageContainer variant="app">
      <div className="flex flex-col h-full p-6">
        <CalendarNav date={date} setDate={setDate} />

        <div className="flex-1 min-h-0">
          {loading ? (
            <div className="h-full w-full flex items-center justify-center bg-muted/10 rounded-xl border border-dashed">
              <p className="text-muted-foreground animate-pulse">Loading appointments...</p>
            </div>
          ) : (
            <CalendarView tasks={tasks} selectedDate={date} />
          )}
        </div>
      </div>
    </PageContainer>
  );
}
