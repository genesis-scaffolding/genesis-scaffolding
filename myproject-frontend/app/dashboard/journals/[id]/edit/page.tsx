import { getJournalAction, getProjectsAction, updateJournalAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { redirect } from "next/navigation";
import { JournalEditForm } from "@/components/dashboard/journals/journal-edit-form";

export default async function EditJournalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const entry = await getJournalAction(id);
  const projects = await getProjectsAction();

  async function handleUpdate(formData: FormData) {
    "use server";
    const type = formData.get("entry_type") as string;
    await updateJournalAction(id, {
      title: formData.get("title") || null,
      entry_type: formData.get("entry_type"),
      reference_date: formData.get("reference_date"),
      content: formData.get("content"),
      project_id: type === "project" ? Number(formData.get("project_id")) : null,
    });
    redirect(`/dashboard/journals/${id}`);
  }

  return (
    <PageContainer variant="prose">
      <PageBody>
        <h1 className="text-2xl font-bold mb-6">Edit Journal Entry</h1>
        <JournalEditForm
          entry={entry}
          projects={projects}
          onUpdate={handleUpdate}
        />
      </PageBody>
    </PageContainer>
  );
}
