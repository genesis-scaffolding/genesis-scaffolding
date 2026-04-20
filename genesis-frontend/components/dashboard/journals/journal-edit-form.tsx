"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { JournalEntry, Project } from "@/types/productivity";

interface JournalEditFormProps {
  entry: JournalEntry;
  projects: Project[];
  onUpdate: (formData: FormData) => Promise<void>;
  onCancel: () => void;
}

export function JournalEditForm({ entry, projects, onUpdate, onCancel }: JournalEditFormProps) {
  return (
    <form action={onUpdate} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="entry_type">Type</Label>
          <select
            id="entry_type"
            name="entry_type"
            defaultValue={entry.entry_type}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
            <option value="project">Project Log</option>
            <option value="general">General</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="reference_date">Reference Date</Label>
          <Input
            id="reference_date"
            name="reference_date"
            type="date"
            defaultValue={entry.reference_date}
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="project_id">Associated Project</Label>
        <select
          id="project_id"
          name="project_id"
          defaultValue={entry.project_id || ""}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">Select a project...</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" name="title" defaultValue={entry.title || ""} placeholder="Optional title..." />
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">Content (Markdown)</Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={entry.content}
          rows={20}
          className="font-mono"
          required
        />
      </div>

      <div className="flex gap-4 justify-end">
        <Button variant="ghost" type="button" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Save Changes</Button>
      </div>
    </form>
  );
}
