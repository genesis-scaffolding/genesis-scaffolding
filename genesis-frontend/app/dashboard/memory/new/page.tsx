"use client";

import { useSearchParams } from "next/navigation";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { MemoryForm } from "@/components/dashboard/memory/memory-form";
import { PageHeader } from "@/components/dashboard/page-header";

export default function NewMemoryPage() {
  const searchParams = useSearchParams();
  const memoryType = (searchParams.get("type") as "event" | "topic") || "topic";

  return (
    <PageContainer variant="prose">
      <PageBody>
        <PageHeader />
        <h1 className="text-2xl font-bold mb-6">
          New {memoryType === "event" ? "Event" : "Topic"}
        </h1>
        <MemoryForm memoryType={memoryType} />
      </PageBody>
    </PageContainer>
  );
}
