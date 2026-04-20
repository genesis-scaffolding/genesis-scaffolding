"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { getEventAction, getTopicAction } from "@/app/actions/memory";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { MemoryForm } from "@/components/dashboard/memory/memory-form";
import { PageHeader } from "@/components/dashboard/page-header";
import { EventLog, TopicalMemory } from "@/types/memory";

export default function EditMemoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ type?: string }>;
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [memoryType, setMemoryType] = useState<"event" | "topic">("topic");
  const [memory, setMemory] = useState<EventLog | TopicalMemory | null>(null);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  useEffect(() => {
    params.then(async ({ id }) => {
      const sp = await searchParams;
      const type = (sp.type as "event" | "topic") || "topic";
      setId(id);
      setMemoryType(type);

      try {
        if (type === "event") {
          const event = await getEventAction(id);
          setMemory(event);
        } else {
          const topic = await getTopicAction(id);
          setMemory(topic);
        }
      } catch (error) {
        console.error("Failed to load memory:", error);
      }
    });
  }, [params, searchParams]);

  useEffect(() => {
    if (updateSuccess && id) {
      router.replace(`/dashboard/memory/${id}?type=${memoryType}`);
    }
  }, [updateSuccess, id, memoryType, router]);

  function handleCancel() {
    if (id) {
      router.replace(`/dashboard/memory/${id}?type=${memoryType}`);
    }
  }

  if (!memory || !id) {
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
        <h1 className="text-2xl font-bold mb-6">Edit Memory</h1>
        <MemoryForm memoryType={memoryType} initialData={memory} />
      </PageBody>
    </PageContainer>
  );
}
