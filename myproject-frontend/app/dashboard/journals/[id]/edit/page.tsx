"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { getJournalAction, getProjectsAction, updateJournalAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { JournalEditForm } from "@/components/dashboard/journals/journal-edit-form";
import { PageHeader } from "@/components/dashboard/page-header";
import { JournalEntry, Project } from "@/types/productivity";

export default function EditJournalPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  useEffect(() => {
    params.then(async ({ id }) => {
      setId(id);
      const [entryData, projectsData] = await Promise.all([
        getJournalAction(id),
        getProjectsAction(),
      ]);
      setEntry(entryData);
      setProjects(projectsData);
    });
  }, [params]);

  async function handleUpdate(formData: FormData) {
    if (!id) return;
    const type = formData.get("entry_type") as string;
    await updateJournalAction(id, {
      title: formData.get("title") || null,
      entry_type: formData.get("entry_type"),
      reference_date: formData.get("reference_date"),
      content: formData.get("content"),
      project_id: type === "project" ? Number(formData.get("project_id")) : null,
    });
    setUpdateSuccess(true);
  }

  useEffect(() => {
    if (updateSuccess && id) {
      router.replace(`/dashboard/journals/${id}`);
    }
  }, [updateSuccess, id, router]);

  function handleCancel() {
    if (id) {
      router.replace(`/dashboard/journals/${id}`);
    }
  }

  if (!entry || !id) {
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
        <PageHeader />
        <h1 className="text-2xl font-bold mb-6">Edit Journal Entry</h1>
        <JournalEditForm
          entry={entry}
          projects={projects}
          onUpdate={handleUpdate}
          onCancel={handleCancel}
        />
      </PageBody>
    </PageContainer>
  );
}
