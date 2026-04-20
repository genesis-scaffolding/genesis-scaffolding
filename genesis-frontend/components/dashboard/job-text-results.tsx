import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { isPathResult, cleanPythonResult } from "@/lib/job-utils";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function JobTextResults({ result }: { result: Record<string, string> | null }) {
  if (!result) return null;

  const textEntries = Object.entries(result).filter(
    ([key, value]) => !isPathResult(value) && !key.toLowerCase().includes('path')
  );

  if (textEntries.length === 0) return null;

  return (
    <div className="space-y-6">
      {textEntries.map(([key, value]) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="text-sm font-medium capitalize">
              {key.replace(/_/g, ' ')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 bg-slate-50 p-4 rounded-md border prose prose-neutral dark:prose-invert max-w-none 
            leading-[1.6]
            prose-p:mb-4 prose-p:last:mb-0
            prose-headings:text-foreground prose-headings:font-semibold
            prose-strong:font-bold">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {cleanPythonResult(value)}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
