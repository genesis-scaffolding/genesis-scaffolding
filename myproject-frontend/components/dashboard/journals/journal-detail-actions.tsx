"use client";

import * as React from "react";
import { Edit3, Trash2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { JournalDeleteDialog } from "@/components/dashboard/journals/journal-delete-dialog";

interface JournalDetailActionsProps {
  journalId: string;
  entryTitle?: string;
}

export function JournalDetailActions({ journalId, entryTitle }: JournalDetailActionsProps) {
  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" asChild>
        <Link href={`/dashboard/journals/${journalId}/edit`}>
          <Edit3 className="mr-2 h-4 w-4" /> Edit Entry
        </Link>
      </Button>
      <JournalDeleteDialog journalId={journalId} entryTitle={entryTitle}>
        <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
          <Trash2 className="mr-2 h-4 w-4" /> Delete
        </Button>
      </JournalDeleteDialog>
    </div>
  );
}
