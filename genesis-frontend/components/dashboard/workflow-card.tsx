import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Settings2, Layers } from 'lucide-react';
import type { WorkflowManifest } from '@/types/workflow';

interface WorkflowCardProps {
  workflow: WorkflowManifest;
}

export function WorkflowCard({ workflow }: WorkflowCardProps) {
  const inputCount = Object.keys(workflow.inputs || {}).length;
  const stepCount = workflow.steps?.length || 0;

  return (
    <Card className="flex flex-col hover:shadow-md transition-all duration-200 border-slate-200">
      <CardHeader>
        <div className="flex justify-between items-start mb-2">
          <Badge variant="outline" className="text-xs font-mono">
            v{workflow.version}
          </Badge>
          <Settings2 className="h-4 w-4 text-muted-foreground/50" />
        </div>
        <CardTitle className="text-xl font-bold line-clamp-1">
          {workflow.name}
        </CardTitle>
        <CardDescription className="line-clamp-2 min-h-[40px]">
          {workflow.description}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1">
        <div className="space-y-2">
          <div className="flex items-center text-sm text-muted-foreground">
            <Layers className="mr-2 h-4 w-4" />
            <span>{stepCount} Pipeline {stepCount === 1 ? 'Step' : 'Steps'}</span>
          </div>
          <div className="flex items-center text-sm text-muted-foreground">
            <div className="mr-2 h-4 w-4 flex items-center justify-center font-bold text-[10px] border rounded-sm">
              IN
            </div>
            <span>{inputCount} Configurable {inputCount === 1 ? 'Input' : 'Inputs'}</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="border-t bg-slate-50/50 p-4">
        <Button asChild className="w-full shadow-sm" variant="default">
          <Link href={`/dashboard/workflows/${workflow.id}`}>
            <Play className="mr-2 h-4 w-4 fill-current" /> Launch Workflow
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
