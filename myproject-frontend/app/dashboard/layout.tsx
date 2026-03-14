import { ReactNode } from 'react';
import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/app/actions/auth';
import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarTrigger
} from '@/components/ui/sidebar';
import {
  LayoutDashboard,
  Box,
  Activity,
  FileCode,
  AlarmClock,
  MessagesSquare,
  History,
  Zap,
  User,
  Settings,
  Briefcase,
  ListTodo,
  BookOpen,
} from 'lucide-react';
import LogoutButton from '@/components/auth/logout-button';
import Link from 'next/link';
import DynamicHeader from '@/components/dashboard/dynamic-header';

// Structured navigation groups for better UX
const navGroups = [
  {
    label: "Productivity", // --- NEW GROUP ---
    items: [
      {
        title: "Projects",
        url: "/dashboard/projects",
        icon: Briefcase,
        tooltip: "Manage long-term goals"
      },
      {
        title: "Tasks",
        url: "/dashboard/tasks",
        icon: ListTodo,
        tooltip: "View global backlog"
      },
      {
        title: "Journal",
        url: "/dashboard/journals",
        icon: BookOpen,
        tooltip: "Daily and weekly reflections"
      }
    ]
  },
  {
    label: "Interaction",
    items: [
      {
        title: "Agents",
        url: "/dashboard/agents",
        icon: MessagesSquare,
        tooltip: "Chat with AI Agents"
      },
      {
        title: "Chat History", // New Navigation Item
        url: "/dashboard/history",
        icon: History,
        tooltip: "Resume past conversations"
      }
    ]
  },
  {
    label: "Automation",
    items: [
      {
        title: "Workflows",
        url: "/dashboard/workflows",
        icon: Zap,
        tooltip: "Execute background tasks"
      },
      {
        title: "Schedules",
        url: "/dashboard/schedules",
        icon: AlarmClock,
        tooltip: "Manage cron jobs"
      },
      {
        title: "Activity",
        url: "/dashboard/jobs",
        icon: Activity,
        tooltip: "Monitor background jobs"
      },
    ]
  },
  {
    label: "Knowledge",
    items: [
      {
        title: "Sandbox",
        url: "/dashboard/sandbox",
        icon: Box,
        tooltip: "Manage AI context & files"
      },
    ]
  }
];

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();

  if (!user) {
    redirect('/login');
  }

  return (
    <SidebarProvider className="flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden">
      {/* Navigation Sidebar */}
      <Sidebar collapsible="icon" className="border-r">
        <SidebarHeader className="px-4 py-4">
          <Link href="/dashboard/">
            <div className="flex items-center gap-3 font-semibold group-data-[collapsible=icon]:justify-center">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-white dark:text-slate-900">
                <FileCode className="h-5 w-5" />
              </div>
              <span className="group-data-[collapsible=icon]:hidden uppercase font-black tracking-tighter text-xl text-slate-900 dark:text-white">
                myproject
              </span>
            </div>
          </Link>
        </SidebarHeader>

        <SidebarContent className="gap-0">
          {/* Dashboard / Home is now a top-level item above the groups */}
          <SidebarGroup>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="Home Dashboard">
                  <Link href="/dashboard">
                    <LayoutDashboard className="h-4 w-4" />
                    <span>Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>

          {/* Render grouped navigation */}
          {navGroups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel className="px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                {group.label}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild tooltip={item.tooltip}>
                        <Link href={item.url}>
                          <item.icon className="h-4 w-4" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </SidebarContent>

        <SidebarFooter className="border-t bg-slate-50/50 p-2 dark:bg-slate-900/50">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                size="lg"
                tooltip="Workspace Settings"
                className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                <Link href="/dashboard/settings" className="flex items-center gap-3 px-2">
                  {/* User Icon/Avatar - Always visible even when collapsed */}
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-800">
                    <User className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                  </div>

                  {/* User Info - Hidden when collapsed */}
                  <div className="flex flex-1 flex-col overflow-hidden text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                    <span className="truncate font-semibold uppercase">{user.username}</span>
                    <span className="truncate text-[10px] text-muted-foreground italic">Workspace Settings</span>
                  </div>

                  {/* Add a small settings icon at the end for clarity */}
                  <Settings className="ml-auto h-3 w-3 opacity-50 group-data-[collapsible=icon]:hidden" />
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>

          <div className="mt-2 px-2">
            <LogoutButton />
          </div>
        </SidebarFooter>
      </Sidebar>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden bg-background">
        <header className="shrink-0 flex h-14 items-center gap-4 border-b bg-white/50 px-6 backdrop-blur-md dark:bg-slate-950/50">
          <SidebarTrigger />
          <div className="h-4 w-[1px] bg-slate-200 dark:bg-slate-800" /> {/* Clean Divider */}
          <div className="flex-1">
            <DynamicHeader />
          </div>
        </header>

        {/* Added a subtle background color to main area to pop the chat bubbles */}
        <main className="flex-1 min-h-0 overflow-y-hidden flex flex-col bg-slate-50/30 transition-all duration-300 dark:bg-slate-950/20">
          {children}
        </main>
      </div>
    </SidebarProvider>
  );
}
