import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { SettingsNav } from "@/components/dashboard/settings-nav";
import { Separator } from "@/components/ui/separator";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <PageContainer variant="prose">
      <PageBody>
        <div className="space-y-0.5">
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Manage your workspace preferences and system configurations.
          </p>
        </div>

        <SettingsNav />

        {/* This div ensures content doesn't "jump" during transitions */}
        <div className="flex-1 min-h-0">
          {children}
        </div>
      </PageBody>
    </PageContainer>
  );
}
