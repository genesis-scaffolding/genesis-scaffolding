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
import { deleteJournalAction } from "@/app/actions/productivity";

interface JournalDeleteDialogProps {
  journalId: string;
  entryTitle?: string;
  children: React.ReactNode;
}

export function JournalDeleteDialog({
  journalId,
  entryTitle,
  children,
}: JournalDeleteDialogProps) {
  const [open, setOpen] = React.useState(false);

  const handleDelete = async () => {
    try {
      await deleteJournalAction(journalId);
    } catch (error) {
      console.error("Failed to delete journal entry:", error);
      return;
    }

    setOpen(false);
    redirect("/dashboard/journals");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Entry?</DialogTitle>
          <DialogDescription>
            {entryTitle
              ? `Are you sure you want to delete "${entryTitle}"? This action cannot be undone.`
              : "Are you sure you want to delete this journal entry? This action cannot be undone."}
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
