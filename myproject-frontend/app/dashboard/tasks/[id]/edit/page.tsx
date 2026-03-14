import { getTaskAction, getProjectsAction, updateTaskAction, deleteTaskAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Folder, Calendar, FileText } from "lucide-react";
import Link from "next/link";

export default async function EditTaskPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;
  const task = await getTaskAction(id);
  const projects = await getProjectsAction();

  async function handleUpdate(formData: FormData) {
    "use server";
    const selectedProjectIds = projects
      .filter(p => formData.get(`project-${p.id}`) === "on")
      .map(p => p.id);

    await updateTaskAction(Number(id), {
      title: formData.get("title"),
      description: formData.get("description"),
      status: formData.get("status"),
      assigned_date: formData.get("assigned_date") || null,
      hard_deadline: formData.get("hard_deadline") || null,
      start_time: formData.get("start_time") || null,
      duration_minutes: formData.get("duration_minutes") ? Number(formData.get("duration_minutes")) : null,
      project_ids: selectedProjectIds,
    });

    redirect(`/dashboard/tasks/${id}`);
  }

  async function handleDelete() {
    "use server";
    await deleteTaskAction(id);
    redirect("/dashboard/tasks");
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">Edit Task</h1>
          <Badge variant="outline">ID: {task.id}</Badge>
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
                <Input id="assigned_date" name="assigned_date" type="date" defaultValue={task.assigned_date || ""} />
                <p className="text-[10px] text-muted-foreground">Your personal plan: When you intend to start or do this task.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="hard_deadline">Hard Deadline</Label>
                <Input id="hard_deadline" name="hard_deadline" type="date" defaultValue={task.hard_deadline?.split('T')[0] || ""} />
                <p className="text-[10px] text-destructive">The actual limit: When this task MUST be finished.</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="start_time">Start Time</Label>
                <Input id="start_time" name="start_time" type="time" defaultValue={task.start_time || ""} />
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
            <Button variant="destructive" type="button" form="delete-form">Delete Task</Button>
            <div className="flex gap-2">
              <Button variant="ghost" type="button" asChild><Link href={`/dashboard/tasks/${task.id}`}>Cancel</Link></Button>
              <Button type="submit">Update Task</Button>
            </div>
          </div>
        </form>

        <form id="delete-form" action={handleDelete} className="hidden" />
      </PageBody>
    </PageContainer>
  );
}
