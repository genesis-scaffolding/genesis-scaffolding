"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { createTaskAction } from "@/app/actions/productivity";
import { useRouter } from "next/navigation";

export function QuickAddTask({ defaultProjectId }: { defaultProjectId?: number }) {
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || loading) return;

    setLoading(true);
    try {
      await createTaskAction({
        title: title.trim(),
        project_ids: defaultProjectId ? [defaultProjectId] : [],
        status: "todo",
      });
      setTitle("");
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative group">
      <Plus className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Add a new task... (Press Enter)"
        className="pl-10 h-12 bg-card border-dashed focus:border-solid transition-all"
        disabled={loading}
      />
    </form>
  );
}
