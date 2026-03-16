// components/dashboard/calendar/calendar-nav.tsx
'use client'
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from "lucide-react";
import { format } from "date-fns";

export function CalendarNav({ date, setDate }: { date: Date, setDate: (d: Date) => void }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Calendar</h1>
        <span className="text-muted-foreground font-medium">
          {format(date, "MMMM yyyy")}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => setDate(new Date())}>
          Today
        </Button>
        <div className="flex items-center border rounded-md">
          <Button variant="ghost" size="icon" onClick={() => setDate(new Date(date.setDate(date.getDate() - 7)))}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="w-px h-4 bg-border" />
          <Button variant="ghost" size="icon" onClick={() => setDate(new Date(date.setDate(date.getDate() + 7)))}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
