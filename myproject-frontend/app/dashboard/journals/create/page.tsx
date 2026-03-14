import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { createJournalAction, getProjectsAction } from "@/app/actions/productivity";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export default async function CreateJournalPage() {
  const projects = await getProjectsAction();

  async function handleSubmit(formData: FormData) {
    "use server";
    const data = {
      title: formData.get("title") || null,
      entry_type: formData.get("entry_type"),
      reference_date: formData.get("reference_date"),
      content: formData.get("content"),
      project_id: formData.get("project_id") || null,
    };

    await createJournalAction(data);
    redirect("/dashboard/journals");
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <h1 className="text-2xl font-bold mb-6">Write Journal Entry</h1>
        <form action={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="entry_type">Type</Label>
              <select id="entry_type" name="entry_type" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="project">Project Log</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reference_date">Reference Date</Label>
              <Input id="reference_date" name="reference_date" type="date" defaultValue={new Date().toISOString().split('T')[0]} required />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="project_id">Associate with Project (Optional)</Label>
            <select id="project_id" name="project_id" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">None</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Title (Optional)</Label>
            <Input id="title" name="title" placeholder="e.g. Morning Reflection" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="content">Content (Supports Markdown)</Label>
            <Textarea id="content" name="content" rows={15} placeholder="Write your thoughts here..." required className="font-mono" />
          </div>

          <div className="flex gap-4 justify-end">
            <Button variant="ghost" type="button">Cancel</Button>
            <Button type="submit">Save Entry</Button>
          </div>
        </form>
      </PageBody>
    </PageContainer>
  );
}
