import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { createProjectAction } from "@/app/actions/productivity";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import Link from "next/link";

export default function CreateProjectPage() {
  async function handleSubmit(formData: FormData) {
    "use server";
    const data = {
      name: formData.get("name"),
      description: formData.get("description"),
      deadline: formData.get("deadline") || null,
      status: "todo",
    };

    await createProjectAction(data);
    redirect("/dashboard/projects");
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <h1 className="text-2xl font-bold mb-6">Create New Project</h1>
        <form action={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input id="name" name="name" placeholder="e.g., Website Redesign" required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" name="description" placeholder="What is this project about?" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="deadline">Deadline (Optional)</Label>
            <Input id="deadline" name="deadline" type="date" />
          </div>

          <div className="flex gap-4 justify-end">
            <Button variant="ghost" asChild>
              <Link href={`/dashboard/projects`}>Cancel</Link>
            </Button>
            <Button type="submit">Create Project</Button>
          </div>
        </form>
      </PageBody>
    </PageContainer>
  );
}
