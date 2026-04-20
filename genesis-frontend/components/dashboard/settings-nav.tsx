"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const tabs = [
  { name: "General", href: "/dashboard/settings" },
  { name: "LLM Configuration", href: "/dashboard/settings/llm" },
  // { name: "Database", href: "/dashboard/settings/database" }, // Future proofing
];

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <div className="w-full border-b shrink-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <nav
        className="flex space-x-8 overflow-x-auto no-scrollbar scroll-smooth"
        aria-label="Settings"
      >
        {tabs.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={cn(
                "whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
              )}
            >
              {tab.name}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
