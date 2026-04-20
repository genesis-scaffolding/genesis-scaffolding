"use client";

import { usePathname } from "next/navigation";
import { Home } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

// Map your route segments to readable titles
const routeMap: Record<string, string> = {
  workflows: "Workflows",
  jobs: "Job History",
  sandbox: "Sandbox",
  settings: "Settings",
};

export default function DynamicHeader() {
  const pathname = usePathname();

  // Split path into segments: /dashboard/jobs -> ['dashboard', 'jobs']
  const segments = pathname.split("/").filter(Boolean);

  console.log(pathname)
  console.log(segments)
  return (
    <div className="flex flex-col gap-1">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/" className="flex items-center gap-1">
              <Home className="h-3 w-3" />
            </BreadcrumbLink>
          </BreadcrumbItem>

          {segments.map((segment, index) => {
            const path = `/${segments.slice(0, index + 1).join("/")}`;
            const isLast = index === segments.length - 1;
            const label = routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);

            return (
              <span key={path} className="flex items-center gap-2">
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage>{label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={path}>{label}</BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </span>
            );
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );
}
