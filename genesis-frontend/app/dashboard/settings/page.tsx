// app/dashboard/settings/page.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export default function GeneralSettingsPage() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Workspace Profile</h2>
          <p className="text-sm text-muted-foreground">
            Update your workspace identity and display information.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Identity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Workspace Name</Label>
              <Input id="name" defaultValue="Personal Workspace" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Administrative Email</Label>
              <Input id="email" defaultValue="admin@genesis.local" />
            </div>
            <Button className="w-fit">Update Profile</Button>
          </CardContent>
        </Card>
      </section>

      <Separator />

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Regional & Localization</h2>
          <p className="text-sm text-muted-foreground">
            Configure how time and dates are handled in your logs and schedules.
          </p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Input id="timezone" defaultValue="Australia/Adelaide" disabled />
              <p className="text-[10px] text-muted-foreground italic">
                Timezone is currently managed via system environment variables.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
