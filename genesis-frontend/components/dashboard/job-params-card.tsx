import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function JobParamsCard({ inputs }: { inputs: Record<string, any> }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Inputs
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-4">
          {Object.entries(inputs).map(([key, value]) => (
            <div key={key} className="flex flex-col gap-1 border-b border-slate-50 pb-2 last:border-0">
              <dt className="text-xs font-bold text-slate-500 capitalize">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="text-sm font-mono break-all bg-slate-50 p-1.5 rounded">
                {Array.isArray(value) ? value.join(', ') : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
