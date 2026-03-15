"use client";

import { useState } from "react";
import { Task, Project } from "@/types/productivity";
import { Checkbox } from "@/components/ui/checkbox";
import { BulkActionBar } from "./bulk-action-bar";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Edit2 } from "lucide-react";

export function TaskTable({ tasks, projects }: { tasks: Task[], projects: Project[] }) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const toggleSelect = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const getProjectName = (id: number) => projects.find(p => p.id === id)?.name || "Inbox";

  return (
    <div className="relative pb-20">
      <div className="rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50 text-muted-foreground">
              <th className="p-4 w-10"></th>
              <th className="p-4 text-left font-medium">Task</th>
              <th className="p-4 text-left font-medium">Project</th>
              <th className="p-4 text-left font-medium">Status</th>
              <th className="p-4 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {tasks.map((task) => (
              <tr key={task.id} className="group hover:bg-accent/40 transition-colors">
                <td className="p-4">
                  <Checkbox
                    checked={selectedIds.includes(task.id)}
                    onCheckedChange={() => toggleSelect(task.id)}
                  />
                </td>
                <td className="p-4">
                  <Link href={`/dashboard/tasks/${task.id}`} className="hover:underline">
                    <div className="font-medium text-primary">{task.title}</div>
                  </Link>
                  {task.assigned_date && (
                    <div className="text-xs text-muted-foreground">Scheduled: {task.assigned_date}</div>
                  )}
                </td>
                <td className="p-4">
                  {task.project_ids.length > 0 ? (
                    <Badge variant="secondary" className="font-normal">
                      {getProjectName(task.project_ids[0])}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground text-xs italic">Unassigned</span>
                  )}
                </td>
                <td className="p-4 capitalize">
                  <span className={`text-xs px-2 py-1 rounded-full border ${task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                    }`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="p-4">
                  <Link href={`/dashboard/tasks/${task.id}/edit`} className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <Edit2 className="h-4 w-4 text-muted-foreground hover:text-primary" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <BulkActionBar
        selectedIds={selectedIds}
        onClear={() => setSelectedIds([])}
        projects={projects}
      />
    </div>
  );
}
