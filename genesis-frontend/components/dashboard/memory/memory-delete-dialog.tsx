"use client";

import * as React from "react";
import { redirect } from "next/navigation";
import { Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { deleteEventAction, deleteTopicAction } from "@/app/actions/memory";

interface MemoryDeleteDialogProps {
  id: number;
  memoryType: "event" | "topic";
  subject?: string;
  children: React.ReactNode;
}

export function MemoryDeleteDialog({
  id,
  memoryType,
  subject,
  children,
}: MemoryDeleteDialogProps) {
  const [open, setOpen] = React.useState(false);

  const handleDelete = async () => {
    try {
      if (memoryType === "event") {
        await deleteEventAction(id);
      } else {
        await deleteTopicAction(id);
      }
    } catch (error) {
      console.error("Failed to delete memory:", error);
      return;
    }

    setOpen(false);
    redirect("/dashboard/memory");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {memoryType === "event" ? "Event" : "Topic"}?</DialogTitle>
          <DialogDescription>
            {subject
              ? `Are you sure you want to delete "${subject}"? This action cannot be undone.`
              : `Are you sure you want to delete this ${memoryType}? This action cannot be undone.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
