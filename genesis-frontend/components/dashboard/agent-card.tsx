"use client";

import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Wrench, Users, MoreVertical, Pencil, Trash2, Star } from 'lucide-react';
import { Agent } from '@/types/chat';
import { StartChatButton } from './start-chat-button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { deleteAgentAction, updateAgentAction } from '@/app/actions/chat';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner'; // Or your preferred toast library
import { cn } from '@/lib/utils';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isTogglingDefault, setIsTogglingDefault] = useState(false);
  const modelDisplay = agent.model_name || 'Default Model';

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${agent.name}"?`)) return;

    setIsDeleting(true);
    try {
      await deleteAgentAction(agent.id);
      toast.success("Agent deleted successfully");
      router.refresh();
    } catch (error) {
      toast.error("Failed to delete agent");
      console.error(error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleToggleDefault = async () => {
    setIsTogglingDefault(true);
    try {
      await updateAgentAction(agent.id, {
        description: agent.description,
        system_prompt: agent.system_prompt ?? "",
        interactive: agent.interactive,
        allowed_tools: agent.allowed_tools,
        allowed_agents: agent.allowed_agents,
        model_name: agent.model_name,
        is_default: !agent.is_default,
      });
      toast.success(agent.is_default ? 'Removed as default' : 'Set as default');
      router.refresh();
    } catch (error) {
      toast.error('Failed to update default agent');
      console.error(error);
    } finally {
      setIsTogglingDefault(false);
    }
  };

  return (
    <Card className={`flex flex-col hover:shadow-md transition-all duration-200 border-slate-200 ${isDeleting ? 'opacity-50 grayscale' : ''}`}>
      <CardHeader>
        <div className="flex justify-between items-center mb-2 h-8">
          <Badge
            variant="secondary"
            className="text-[10px] font-mono uppercase tracking-wider max-w-[120px] truncate block"
            title={modelDisplay}
          >
            {modelDisplay}
          </Badge>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleDefault}
              disabled={isTogglingDefault}
              className={cn(
                "h-8 w-8 text-muted-foreground hover:text-yellow-500 transition-colors",
                agent.is_default && "text-yellow-500"
              )}
              title={agent.is_default ? 'Unset as default' : 'Set as default'}
            >
              {agent.is_default ? (
                <Star className="h-4 w-4 fill-yellow-500" />
              ) : (
                <Star className="h-4 w-4" />
              )}
            </Button>

            {/* Show options only if NOT read_only */}
            {!agent.read_only && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4 text-muted-foreground" />
                    <span className="sr-only">Open menu</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <Link href={`/dashboard/agents/${agent.id}/edit`} className="flex items-center cursor-pointer">
                      <Pencil className="mr-2 h-4 w-4" />
                      <span>Edit Agent</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleDelete}
                    className="text-destructive focus:text-destructive cursor-pointer"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    <span>Delete Agent</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>

        <Link href={`/dashboard/agents/${agent.id}`} className="group/title block space-y-1">
          <CardTitle className="text-xl font-bold line-clamp-1 group-hover/title:text-blue-600 transition-colors">
            {agent.name}
          </CardTitle>
          <CardDescription className="line-clamp-2 min-h-[40px]">
            {agent.description}
          </CardDescription>
        </Link>
      </CardHeader>

      <CardContent className="flex-1">
        <div className="space-y-3">
          <div className="flex items-center text-sm text-muted-foreground">
            <Wrench className="mr-2 h-4 w-4" />
            <span>{agent.allowed_tools.length} Tools Available</span>
          </div>
          <div className="flex items-center text-sm text-muted-foreground">
            <Users className="mr-2 h-4 w-4" />
            <span>{agent.allowed_agents.length} Collaborators</span>
          </div>

          <div className="flex flex-wrap gap-1 pt-2">
            {agent.interactive && (
              <Badge variant="outline" className="text-[10px] bg-green-50 text-green-700 border-green-200">
                Interactive
              </Badge>
            )}
            {agent.read_only && (
              <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-500 border-slate-200">
                System (Read-only)
              </Badge>
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="border-t bg-slate-50/50 p-4">
        <StartChatButton agentId={agent.id} agentName={agent.name} />
      </CardFooter>
    </Card>
  );
}
