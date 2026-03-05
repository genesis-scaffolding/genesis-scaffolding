import React from "react";
import { cn } from "@/lib/utils";

type PageVariant = "prose" | "dashboard" | "app";

interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: PageVariant;
  children: React.ReactNode;
}

const PageContainer = React.forwardRef<HTMLDivElement, PageContainerProps>(
  ({ variant = "dashboard", children, className, ...props }, ref) => {

    // Define variant-specific styles
    const variantStyles: Record<PageVariant, string> = {
      // 1. Prose: Centered, constrained width, readable padding
      prose: "max-w-5xl mx-auto p-4 md:p-10 overflow-y-auto",

      // 2. Dashboard: Wider, standard padding for grids/tables
      dashboard: "max-w-[1600px] mx-auto p-4 md:p-6 overflow-y-auto",

      // 3. App: Edge-to-edge, no scroll (internal components handle scroll)
      app: "max-w-none p-0 overflow-hidden flex flex-col",
    };

    return (
      <div
        ref={ref}
        className={cn(
          // Base styles for all pages: fill the slot provided by layout
          "h-full w-full min-h-0 min-w-0",
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

const PageBody = React.forwardRef<HTMLDivElement, PageContainerProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        className={cn(
          "flex flex-col gap-6", // This is your repeated "Source of Truth"
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

PageContainer.displayName = "PageContainer";
PageBody.displayName = "PageBody"

export { PageContainer, PageBody };
