"use client";

import { JournalEntry, Project } from "@/types/productivity";
import { format } from "date-fns";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Edit2, FileText } from "lucide-react";

export function JournalTable({ entries, projects }: { entries: JournalEntry[], projects: Project[] }) {
  const getProjectName = (id?: number) => projects.find(p => p.id === id)?.name || "-";

  return (
    <div className="rounded-md border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50 text-muted-foreground">
            <th className="p-4 text-left font-medium">Date</th>
            <th className="p-4 text-left font-medium">Title</th>
            <th className="p-4 text-left font-medium">Type</th>
            <th className="p-4 text-left font-medium">Project</th>
            <th className="p-4 w-10"></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {entries.map((entry) => (
            <tr key={entry.id} className="group hover:bg-accent/40 transition-colors">
              <td className="p-4 whitespace-nowrap font-mono text-xs">
                {format(new Date(entry.reference_date), "yyyy-MM-dd")}
              </td>
              <td className="p-4">
                <Link href={`/dashboard/journals/${entry.id}`} className="hover:underline font-medium text-primary flex items-center gap-2">
                  <FileText className="h-3 w-3 text-muted-foreground" />
                  {entry.title || "Untitled Entry"}
                </Link>
              </td>
              <td className="p-4">
                <Badge variant="outline" className="capitalize text-[10px] px-1.5 py-0">
                  {entry.entry_type}
                </Badge>
              </td>
              <td className="p-4 text-muted-foreground">
                {entry.project_id ? getProjectName(entry.project_id) : "-"}
              </td>
              <td className="p-4">
                <Link href={`/dashboard/journals/${entry.id}/edit`} className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <Edit2 className="h-4 w-4 text-muted-foreground hover:text-primary" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
