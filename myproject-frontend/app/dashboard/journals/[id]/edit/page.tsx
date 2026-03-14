import { getJournalAction, getProjectsAction, updateJournalAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import Link from "next/link";

export default async function EditJournalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const entry = await getJournalAction(id);
  const projects = await getProjectsAction();

  async function handleUpdate(formData: FormData) {
    "use server";
    await updateJournalAction(id, {
      title: formData.get("title") || null,
      entry_type: formData.get("entry_type"),
      reference_date: formData.get("reference_date"),
      content: formData.get("content"),
      project_id: formData.get("project_id") || null,
    });
    redirect(`/dashboard/journals/${id}`);
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <h1 className="text-2xl font-bold mb-6">Edit Journal Entry</h1>
        <form action={handleUpdate} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="entry_type">Type</Label>
              <select id="entry_type" name="entry_type" defaultValue={entry.entry_type} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="project">Project Log</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reference_date">Reference Date</Label>
              <Input id="reference_date" name="reference_date" type="date" defaultValue={entry.reference_date} required />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="project_id">Associated Project</Label>
            <select id="project_id" name="project_id" defaultValue={entry.project_id || ""} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">None</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input id="title" name="title" defaultValue={entry.title || ""} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="content">Content (Markdown)</Label>
            <Textarea id="content" name="content" defaultValue={entry.content} rows={20} className="font-mono" required />
          </div>

          <div className="flex gap-4 justify-end">
            <Button variant="ghost" asChild><Link href={`/dashboard/journals/${id}`}>Cancel</Link></Button>
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </PageBody>
    </PageContainer>
  );
}
