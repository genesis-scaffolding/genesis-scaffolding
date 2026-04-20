'use client';

import { useJob } from "./job-context";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle2, Loader2, Wifi, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";

export function JobStatusBanner() {
  const { job, isConnected } = useJob();

  const statusConfig = {
    pending: { label: "Pending", color: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20", icon: Loader2 },
    running: { label: "Processing", color: "bg-blue-500/10 text-blue-600 border-blue-500/20", icon: Loader2 },
    completed: { label: "Completed", color: "bg-green-500/10 text-green-600 border-green-500/20", icon: CheckCircle2 },
    failed: { label: "Failed", color: "bg-red-500/10 text-red-600 border-red-500/20", icon: AlertCircle },
  };

  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <div className="space-y-4">
      <div className={cn("flex flex-col gap-4 p-4 rounded-xl border shadow-sm bg-card", config.color)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <Icon className={cn("h-5 w-5", job.status === 'running' && "animate-spin")} />
            {config.label}
          </div>

          {/* SSE Connection Indicator */}
          {job.status === 'running' && (
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md bg-white/50 border border-current">
              {isConnected ? (
                <>
                  <Wifi className="h-3 w-3" /> Live
                </>
              ) : (
                <>
                  <WifiOff className="h-3 w-3" /> Reconnecting
                </>
              )}
            </div>
          )}
        </div>

        {job.error_message && (
          <div className="text-sm bg-red-500/10 p-3 rounded-lg border border-red-500/20 font-mono break-all text-red-700">
            <strong>Error:</strong> {job.error_message}
          </div>
        )}
      </div>
    </div>
  );
}
