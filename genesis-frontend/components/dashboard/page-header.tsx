"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  backLabel?: string;
  backHref?: string; // Optional: Force a specific link instead of browser back
  children?: React.ReactNode; // For the Edit button or other actions
  className?: string;
}

export function PageHeader({
  backLabel = "Back",
  backHref,
  children,
  className
}: PageHeaderProps) {
  const router = useRouter();

  const handleBack = () => {
    // 1. If a manual override is provided, use it
    if (backHref) {
      router.push(backHref);
      return;
    }

    // 2. Check the referrer
    const referrer = typeof document !== 'undefined' ? document.referrer : "";

    // Logic: If previous page was an "edit" page, skip it and go back 2 steps
    // We check for "/edit" in the URL string
    const isFromEditPage = referrer.toLowerCase().includes("/edit");

    if (isFromEditPage && window.history.length > 2) {
      window.history.go(-2);
    } else {
      router.back();
    }
  };

  return (
    <div className={cn("flex items-center justify-between", className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleBack}
        className="-ml-2 text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        {backLabel}
      </Button>

      <div className="flex items-center gap-2">
        {children}
      </div>
    </div>
  );
}
