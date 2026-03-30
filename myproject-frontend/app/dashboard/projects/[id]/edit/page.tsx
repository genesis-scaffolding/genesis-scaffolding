"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect, useTransition } from "react";
import { getProjectAction, updateProjectAction, deleteProjectAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export default function EditProjectPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [project, setProject] = useState<{ name: string; description?: string; deadline?: string; status: string } | null>(null);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    params.then(({ id }) => {
      setId(id);
      getProjectAction(id).then(setProject);
    });
  }, [params]);

  async function handleUpdate(formData: FormData) {
    if (!id) return;
    await updateProjectAction(id, {
      name: formData.get("name") as string,
      description: formData.get("description") as string,
      deadline: (formData.get("deadline") as string) || null,
      status: formData.get("status") as string,
    });
    setUpdateSuccess(true);
  }

  async function handleDelete(formData: FormData) {
    if (!id) return;
    await deleteProjectAction(id);
    router.replace("/dashboard/projects");
  }

  useEffect(() => {
    if (updateSuccess && id) {
      router.replace(`/dashboard/projects/${id}`);
    }
  }, [updateSuccess, id, router]);

  function handleCancel() {
    if (id) {
      router.replace(`/dashboard/projects/${id}`);
    }
  }

  if (!project || !id) {
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
        <h1 className="text-2xl font-bold mb-6">Edit Project</h1>

        <form action={handleUpdate} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input id="name" name="name" defaultValue={project.name} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" name="description" defaultValue={project.description || ""} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                name="status"
                defaultValue={project.status}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="backlog">Backlog</option>
                <option value="todo">Todo</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="canceled">Canceled</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="deadline">Deadline</Label>
              <Input id="deadline" name="deadline" type="date" defaultValue={project.deadline?.split('T')[0] || ""} />
            </div>
          </div>

          <div className="flex gap-4 justify-between pt-4">
            {/*
               Use formAction here. This button will trigger handleDelete
               instead of the main form's handleUpdate action.
            */}
            <Button
              variant="destructive"
              type="submit"
              formAction={handleDelete}
            >
              Delete Project
            </Button>

            <div className="flex gap-2">
              <Button variant="ghost" type="button" onClick={handleCancel}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </form>
      </PageBody>
    </PageContainer>
  );
}
