"use client";

import * as React from "react";
import { Project, Status } from "@/types/productivity";
import { ProjectCard } from "./project-card";
import { CheckCircle2, ChevronDown, Circle, Clock, ListTodo, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// Section order: active states first, terminal states last. Mirrors
// STATUS_WEIGHTS in types/productivity.ts (in_progress > todo > backlog >
// completed > canceled).
const STATUS_SECTIONS: {
  status: Status;
  label: string;
  icon: React.ElementType;
  collapsible: boolean;
}[] = [
  { status: "in_progress", label: "In Progress", icon: Clock, collapsible: false },
  { status: "todo", label: "To Do", icon: Circle, collapsible: false },
  { status: "backlog", label: "Backlog", icon: ListTodo, collapsible: false },
  { status: "completed", label: "Completed", icon: CheckCircle2, collapsible: true },
  { status: "canceled", label: "Canceled", icon: XCircle, collapsible: true },
];

// Statuses collapsed by default on first render. Kept as a constant so
// toggling a section is just a set add/remove.
const DEFAULT_COLLAPSED: ReadonlySet<Status> = new Set(["completed", "canceled"]);

export function ProjectSections({ projects }: { projects: Project[] }) {
  const [collapsed, setCollapsed] = React.useState<Set<Status>>(
    () => new Set(DEFAULT_COLLAPSED)
  );

  const toggle = React.useCallback((status: Status) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  }, []);

  // Group projects by status, preserving the input order within each group.
  // Unknown statuses (shouldn't happen, but TypeScript is structural) fall
  // into "todo" rather than being dropped.
  const grouped = React.useMemo(() => {
    const groups: Record<Status, Project[]> = {
      backlog: [],
      todo: [],
      in_progress: [],
      completed: [],
      canceled: [],
    };
    for (const project of projects) {
      const bucket = groups[project.status] ?? groups.todo;
      bucket.push(project);
    }
    return groups;
  }, [projects]);

  return (
    <div className="space-y-8">
      {STATUS_SECTIONS.map(({ status, label, icon: Icon, collapsible }) => {
        const sectionProjects = grouped[status];
        const isCollapsed = collapsed.has(status);

        const headerContent = (
          <>
            {collapsible && (
              <ChevronDown
                className={cn(
                  "h-4 w-4 text-muted-foreground transition-transform",
                  isCollapsed && "-rotate-90"
                )}
              />
            )}
            <Icon className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-semibold tracking-tight">{label}</h2>
            <span className="text-sm text-muted-foreground font-normal">
              ({sectionProjects.length})
            </span>
          </>
        );

        return (
          <section key={status} className="space-y-4">
            {collapsible ? (
              <button
                type="button"
                onClick={() => toggle(status)}
                aria-expanded={!isCollapsed}
                className="flex items-center gap-2 w-full text-left"
              >
                {headerContent}
              </button>
            ) : (
              <div className="flex items-center gap-2">{headerContent}</div>
            )}

            {!isCollapsed && sectionProjects.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {sectionProjects.map((project) => (
                  <ProjectCard key={project.id} project={project} />
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
