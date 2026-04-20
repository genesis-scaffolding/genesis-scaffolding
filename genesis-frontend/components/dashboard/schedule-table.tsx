'use client';

import { WorkflowSchedule } from '@/types/schedule';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Calendar, Clock, Trash2, ExternalLink } from 'lucide-react';
import { updateScheduleAction, deleteScheduleAction } from '@/app/actions/schedule';
import { toast } from 'sonner';
import { formatRelativeTime } from '@/lib/date-utils';
import Link from 'next/link';

interface ScheduleTableProps {
  schedules: WorkflowSchedule[];
}

export function ScheduleTable({ schedules }: ScheduleTableProps) {

  const handleToggle = async (schedule: WorkflowSchedule) => {
    try {
      await updateScheduleAction(schedule.id, { enabled: !schedule.enabled });
      toast.success(`Schedule ${!schedule.enabled ? 'enabled' : 'disabled'}`);
    } catch (err) {
      toast.error('Failed to update schedule');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await deleteScheduleAction(id);
      toast.success('Schedule deleted');
    } catch (err) {
      toast.error('Failed to delete schedule');
    }
  };

  return (
    <div className="rounded-md border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Status</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Workflow</TableHead>
            <TableHead>Frequency (Cron)</TableHead>
            <TableHead>Last Run</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {schedules.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                No schedules found. Create one to automate your workflows.
              </TableCell>
            </TableRow>
          )}
          {schedules.map((schedule) => (
            <TableRow key={schedule.id}>
              <TableCell>
                <Switch
                  checked={schedule.enabled}
                  onCheckedChange={() => handleToggle(schedule)}
                />
              </TableCell>
              <TableCell className="font-medium">
                <Link
                  href={`/dashboard/schedules/${schedule.id}`}
                  className="hover:underline hover:text-primary transition-colors"
                >
                  {schedule.name}
                </Link>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="font-mono">
                  {schedule.workflow_id}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  <code className="bg-muted px-1 rounded">{schedule.cron_expression}</code>
                  <span className="text-xs text-muted-foreground">({schedule.timezone})</span>
                </div>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {schedule.last_run_at ? (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatRelativeTime(schedule.last_run_at)}
                  </div>
                ) : 'Never'}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDelete(schedule.id)}
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
