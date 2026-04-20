import React from "react";
import { cn } from "@/lib/utils";
import { FloatingActionMenu } from "./floating-action-menu";

type FloatingMenuPosition = "bottom-right" | "bottom-left" | "top-right" | "top-left";
type PageVariant = "prose" | "dashboard" | "app";

interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: PageVariant;
  hasFloatingActionMenu?: boolean;
  floatingActionMenuLocation?: FloatingMenuPosition;
  floatingActionMenuProjectId?: number; // Added to pass project context
  children: React.ReactNode;
}

const PageContainer = React.forwardRef<HTMLDivElement, PageContainerProps>(
  ({
    variant = "dashboard",
    hasFloatingActionMenu = true, // Default to true
    floatingActionMenuLocation = "bottom-right", // Default to bottom-right
    floatingActionMenuProjectId,
    children,
    className,
    ...props
  },
    ref) => {
    // 1. SCROLLER: This div is ALWAYS full width to keep the scrollbar at the screen edge
    const scrollerStyles: Record<PageVariant, string> = {
      prose: "overflow-y-auto w-full flex-1",
      dashboard: "overflow-y-auto w-full flex-1",
      app: "overflow-hidden flex flex-col w-full flex-1", // App variant doesn't scroll at this level
    };

    // 2. CENTERING BOX: This div constrains the content width
    const innerStyles: Record<PageVariant, string> = {
      prose: "max-w-5xl mx-auto w-full min-h-full",
      dashboard: "max-w-[1600px] mx-auto w-full min-h-full",
      app: "max-w-none w-full h-full flex flex-col",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "h-full min-h-0 min-w-0", // Base height limits
          scrollerStyles[variant],
          className
        )}
        {...props}
      >
        <div className={innerStyles[variant]}>
          {children}

          {hasFloatingActionMenu && (
            <FloatingActionMenu
              position={floatingActionMenuLocation}
              defaultProjectId={floatingActionMenuProjectId}
            />
          )}
        </div>
      </div>
    );
  }
);

const PageBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          // Standard padding and vertical spacing
          "flex flex-col gap-4 p-4 md:p-6 lg:p-10",
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
