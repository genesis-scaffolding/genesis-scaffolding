'use client';

import { useActionState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { logoutAction } from '@/app/actions/auth';
import type { LogoutState } from '@/types/auth';
import { LogOut, Loader2 } from 'lucide-react';
import {
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton
} from '@/components/ui/sidebar';

export default function LogoutButton() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState<LogoutState, FormData>(
    logoutAction,
    {}
  );

  useEffect(() => {
    if (state.success) {
      router.push('/login');
    }
  }, [state.success, router]);

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <form action={formAction} className="w-full">
          <SidebarMenuButton
            disabled={isPending}
            className="w-full text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
            tooltip="Logout"
            type="submit"
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogOut className="h-4 w-4" />
            )}

            {/* The span will automatically hide when sidebar is collapsed thanks to the sidebar group logic */}
            <span className="group-data-[collapsible=icon]:hidden font-medium">
              {isPending ? 'Logging out...' : 'Logout'}
            </span>
          </SidebarMenuButton>

          {state.error && (
            <p className="mt-2 px-2 text-xs text-red-600 group-data-[collapsible=icon]:hidden">
              {state.error}
            </p>
          )}
        </form>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
