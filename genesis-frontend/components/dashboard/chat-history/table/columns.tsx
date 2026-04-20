"use client";

import { ColumnDef, Row } from "@tanstack/react-table";
import { ChatSession } from "@/types/chat";
import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/dashboard/shared/data-table/column-header";
import { Button } from "@/components/ui/button";
import { MessageSquare, Calendar, ArrowRight, Bot } from "lucide-react";
import Link from "next/link";
import { formatRelativeTime } from "@/lib/date-utils";

/**
 * Custom sorting function that forces null/undefined values to the bottom
 * for date columns (updated_at, created_at).
 */
const dateSortingWithNullsLast = (rowA: Row<ChatSession>, rowB: Row<ChatSession>, columnId: string) => {
  const a = rowA.getValue(columnId) as string | null;
  const b = rowB.getValue(columnId) as string | null;

  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;

  const dateA = new Date(a).getTime();
  const dateB = new Date(b).getTime();

  return dateA - dateB;
};

export const getChatHistoryColumns = (): ColumnDef<ChatSession>[] => [
  {
    accessorKey: "agent_id",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Agent" className="w-[150px]" />,
    cell: ({ row }) => {
      const agentId = row.getValue("agent_id") as string;
      return (
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <Badge variant="secondary" className="font-mono text-xs">
            {agentId}
          </Badge>
        </div>
      );
    },
  },
  {
    accessorKey: "title",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Chat Title" />,
    cell: ({ row }) => {
      const session = row.original;
      return (
        <Link
          href={`/dashboard/chats/${session.id}`}
          className="hover:underline hover:text-primary transition-colors flex items-center gap-2"
        >
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          {session.title}
        </Link>
      );
    },
  },
  {
    accessorKey: "is_running",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" className="w-[100px]" />,
    cell: ({ row }) => {
      const isRunning = row.getValue("is_running") as boolean;
      return isRunning ? (
        <Badge className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-green-500/20">
          Active
        </Badge>
      ) : (
        <Badge variant="outline" className="text-muted-foreground">
          Idle
        </Badge>
      );
    },
  },
  {
    accessorKey: "updated_at",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Last Active" className="w-[150px]" />,
    sortingFn: dateSortingWithNullsLast,
    cell: ({ row }) => {
      const updatedAt = row.getValue("updated_at") as string;
      return (
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {formatRelativeTime(updatedAt)}
        </div>
      );
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const session = row.original;
      return (
        <Button asChild variant="ghost" size="sm" className="gap-2">
          <Link href={`/dashboard/chats/${session.id}`}>
            Resume
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      );
    },
  },
];
