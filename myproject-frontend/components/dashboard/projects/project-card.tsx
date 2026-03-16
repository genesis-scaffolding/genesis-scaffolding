import { Project } from "@/types/productivity";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, CheckCircle2, Circle, Clock, MoreVertical } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";

const statusConfig = {
  backlog: { icon: Circle, color: "text-muted-foreground", label: "Backlog" },
  todo: { icon: Clock, color: "text-blue-500", label: "To Do" },
  in_progress: { icon: Clock, color: "text-amber-500", label: "In Progress" },
  completed: { icon: CheckCircle2, color: "text-emerald-500", label: "Done" },
  canceled: { icon: Circle, color: "text-destructive", label: "Canceled" },
};

export function ProjectCard({ project }: { project: Project }) {
  const status = statusConfig[project.status] || statusConfig.todo;
  const StatusIcon = status.icon;

  return (
    <Link href={`/dashboard/projects/${project.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full flex flex-col">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <div className="space-y-1">
            <CardTitle className="text-lg font-bold leading-none">
              {project.name}
            </CardTitle>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {project.description || "No description provided."}
            </p>
          </div>
          <StatusIcon className={`h-5 w-5 ${status.color}`} />
        </CardHeader>
        <CardContent className="mt-auto pt-4">
          <div className="flex flex-wrap gap-2 items-center text-xs text-muted-foreground">
            <Badge variant="secondary" className="font-normal">
              {status.label}
            </Badge>

            {project.deadline && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>{format(new Date(project.deadline), "MMM d, yyyy")}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
