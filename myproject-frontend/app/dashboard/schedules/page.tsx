import Link from 'next/link';
import { Plus, AlarmClock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScheduleTable } from '@/components/dashboard/schedule-table';
import { getSchedulesAction } from '@/app/actions/schedule';
import { PageBody, PageContainer } from '@/components/dashboard/page-container';

export default async function SchedulesPage() {
  // Fetch data on the server
  const schedules = await getSchedulesAction();

  return (
    <PageContainer>
      <PageBody>
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <AlarmClock className="h-8 w-8 text-primary" />
              Schedules
            </h1>
            <p className="text-muted-foreground">
              Manage your recurring workflow automations.
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard/schedules/new">
              <Plus className="mr-2 h-4 w-4" />
              New Schedule
            </Link>
          </Button>
        </div>

        {/* Table Section */}
        <div className="grid gap-4">
          <ScheduleTable schedules={schedules} />
        </div>
      </PageBody>
    </PageContainer>
  );
}
