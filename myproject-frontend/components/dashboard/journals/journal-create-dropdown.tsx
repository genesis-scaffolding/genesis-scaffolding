"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus, CalendarDays, CalendarRange,
  CalendarDays as CalendarIcon, Loader2, ChevronDown
} from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu"; // Ensure correct Shadcn import for Dropdown
import { Button } from "@/components/ui/button";
import {
  format, addDays, subDays, startOfWeek,
  startOfMonth, addMonths, startOfYear, addYears
} from "date-fns";
import { findOrCreateJournalAction } from "@/app/actions/productivity";
import { JournalType } from "@/types/productivity";

export function JournalCreateDropdown() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleCreate = async (type: JournalType, dateObj: Date, title?: string) => {
    setLoading(true);
    try {
      const refDate = format(dateObj, "yyyy-MM-dd");
      const entry = await findOrCreateJournalAction({
        entry_type: type,
        reference_date: refDate,
        title: title || `${type.charAt(0).toUpperCase() + type.slice(1)} - ${refDate}`
      });
      router.push(`/dashboard/journals/${entry.id}/edit`);
    } finally {
      setLoading(false);
    }
  };

  const today = new Date();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
          New Entry
          <ChevronDown className="ml-2 h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Daily</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleCreate('daily', today)}>Today</DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleCreate('daily', subDays(today, 1))}>Yesterday</DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleCreate('daily', addDays(today, 1))}>Tomorrow</DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel>Weekly</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleCreate('weekly', startOfWeek(today, { weekStartsOn: 1 }))}>This Week</DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleCreate('weekly', startOfWeek(addDays(today, 7), { weekStartsOn: 1 }))}>Next Week</DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel>Monthly</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleCreate('monthly', startOfMonth(today))}>This Month</DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleCreate('monthly', startOfMonth(addMonths(today, 1)))}>Next Month</DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel>Yearly</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleCreate('yearly', startOfYear(today))}>This Year</DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleCreate('yearly', startOfYear(addYears(today, 1)))}>Next Year</DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel>Project</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleCreate('project', today)}>Project Note</DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => handleCreate('general', today)}>General Note...</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
