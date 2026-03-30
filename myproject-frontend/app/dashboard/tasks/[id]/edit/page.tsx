"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect, useTransition } from "react";
import { getTaskAction, getProjectsAction, updateTaskAction, deleteTaskAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Folder, Calendar, FileText } from "lucide-react";
import { Status } from "@/types/productivity";


/**
 * Helper to format a UTC ISO string for a 'datetime-local' input.
 * HTML datetime-local expects: YYYY-MM-DDTHH:mm (no Z, no offset)
 */
function formatForInput(utcString?: string) {
  if (!utcString) return "";
  const date = new Date(utcString);
  // This trick gets the local YYYY-MM-DDTHH:mm format regardless of server TZ
  const offset = date.getTimezoneOffset() * 60000;
  const localISOTime = new Date(date.getTime() - offset).toISOString().slice(0, 16);
  return localISOTime;
}

export default function EditTaskPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [task, setTask] = useState<{
    id: number;
    title: string;
    description?: string;
    status: Status;
    assigned_date?: string;
    hard_deadline?: string;
    scheduled_start?: string;
    duration_minutes?: number;
    project_ids: number[];
  } | null>(null);
  const [projects, setProjects] = useState<Array<{ id: number; name: string }>>([]);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    params.then(async ({ id }) => {
      setId(id);
      const [taskData, projectsData] = await Promise.all([
        getTaskAction(id),
        getProjectsAction(),
      ]);
      setTask(taskData);
      setProjects(projectsData);
    });
  }, [params]);

  async function handleUpdate(formData: FormData) {
    if (!id) return;

    const title = formData.get("title") as string;
    const description = (formData.get("description") as string) || undefined;
    const status = formData.get("status") as Status;

    const assigned_date = (formData.get("assigned_date") as string) || undefined;
    const raw_deadline = (formData.get("hard_deadline") as string) || undefined;
    const start_time = (formData.get("start_time") as string) || undefined;
    const duration_minutes = formData.get("duration_minutes")
      ? Number(formData.get("duration_minutes"))
      : undefined;

    // 1. Logic for Hard Deadline
    let hard_deadline: string | undefined = undefined;
    if (raw_deadline) {
      const d = new Date(`${raw_deadline}T23:59:59`);
      hard_deadline = d.toISOString();
    }

    // 2. Logic for Scheduled Start (Appointment)
    const raw_scheduled = formData.get("scheduled_start") as string;
    let scheduled_start: string | undefined = undefined;
    if (raw_scheduled) {
      // Passing a YYYY-MM-DDTHH:mm string to new Date() interprets it as local time
      const d = new Date(raw_scheduled);
      scheduled_start = d.toISOString(); // Automatically converts to UTC
    }

    const selectedProjectIds = projects
      .filter(p => formData.get(`project-${p.id}`) === "on")
      .map(p => p.id);

    await updateTaskAction(Number(id), {
      title,
      description,
      status,
      assigned_date,
      hard_deadline,
      scheduled_start, // Replaces start_time
      duration_minutes,
      project_ids: selectedProjectIds,
    });

    setUpdateSuccess(true);
  }

  async function handleDelete(formData: FormData) {
    if (!id) return;
    await deleteTaskAction(Number(id));
    router.replace("/dashboard/tasks");
  }

  useEffect(() => {
    if (updateSuccess && id) {
      router.replace(`/dashboard/tasks/${id}`);
    }
  }, [updateSuccess, id, router]);

  function handleCancel() {
    if (id) {
      router.replace(`/dashboard/tasks/${id}`);
    }
  }

  if (!task || !id) {
    return (
      <PageContainer variant="prose">
        <PageBody>
          <div className="animate-pulse">Loading...</div>
        </PageBody>
      </PageContainer>
    );
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">Edit Task</h1>
          <Badge variant="outline">ID: {id}</Badge>
        </div>

        <form action={handleUpdate} className="space-y-10">

          {/* GROUP 1: METADATA */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-primary">
              <Folder className="h-4 w-4" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Metadata</h2>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label htmlFor="title">Task Title</Label>
              <Input id="title" name="title" defaultValue={task.title} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <select id="status" name="status" defaultValue={task.status} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="todo">Todo</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="backlog">Backlog</option>
                  <option value="canceled">Canceled</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Associated Projects</Label>
                <div className="border rounded-md p-2 h-24 overflow-y-auto bg-muted/20">
                  {projects.map(p => (
                    <div key={p.id} className="flex items-center space-x-2 py-1">
                      <input type="checkbox" id={`project-${p.id}`} name={`project-${p.id}`} defaultChecked={task.project_ids.includes(p.id)} />
                      <label htmlFor={`project-${p.id}`} className="text-xs truncate">{p.name}</label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* GROUP 2: PLANNING & DATES */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-primary">
              <Calendar className="h-4 w-4" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Planning</h2>
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="assigned_date">Assigned Date</Label>
                <Input
                  id="assigned_date"
                  name="assigned_date"
                  type="date"
                  defaultValue={task.assigned_date || ""}
                />
                <p className="text-[10px] text-muted-foreground">Your personal plan: When you intend to start or do this task.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="hard_deadline">Hard Deadline</Label>
                <Input
                  id="hard_deadline"
                  name="hard_deadline"
                  type="date"
                  defaultValue={task.hard_deadline ? task.hard_deadline.split('T')[0] : ""}
                />
                <p className="text-[10px] text-destructive">The actual limit: When this task MUST be finished.</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="scheduled_start">Scheduled Appointment</Label>
                <Input
                  id="scheduled_start"
                  name="scheduled_start"
                  type="datetime-local"
                  defaultValue={formatForInput(task.scheduled_start)}
                />
                <p className="text-[10px] text-muted-foreground">Fixed time: Blocks your calendar.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration_minutes">Duration (Minutes)</Label>
                <Input id="duration_minutes" name="duration_minutes" type="number" defaultValue={task.duration_minutes || ""} placeholder="e.g. 60" />
              </div>
            </div>
          </section>

          {/* GROUP 3: CONTENT */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-primary">
              <FileText className="h-4 w-4" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Content</h2>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label htmlFor="description">Description (Supports Markdown)</Label>
              <Textarea id="description" name="description" defaultValue={task.description || ""} rows={10} className="font-mono text-sm" />
            </div>
          </section>

          <div className="flex gap-4 justify-between border-t pt-8">
            <Button variant="destructive" type="submit" formAction={handleDelete}>
              Delete Task
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" type="button" onClick={handleCancel}>Cancel</Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "Updating..." : "Update Task"}
              </Button>
            </div>
          </div>
        </form>
      </PageBody>
    </PageContainer>
  );
}
