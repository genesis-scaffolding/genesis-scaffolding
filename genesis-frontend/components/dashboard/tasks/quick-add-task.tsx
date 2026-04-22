"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { Plus, Loader2, Hash, Calendar, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { createTaskAction, deleteTaskAction, getProjectsAction } from "@/app/actions/productivity";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Project } from "@/types/productivity";
import { parseTaskInput } from "@/lib/task-parser";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

export function QuickAddTask({ defaultProjectId, showToast = false, popupDirection = "below" }: { defaultProjectId?: number; showToast?: boolean; popupDirection?: "above" | "below" }) {
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);

  // Suggestion State
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    getProjectsAction().then(setProjects).catch(console.error);
  }, []);

  // 1. Filter projects based on what's typed after the '#'
  const currentQuery = useMemo(() => {
    const parts = inputValue.split("#");
    return parts.length > 1 ? parts.pop()?.toLowerCase() || "" : "";
  }, [inputValue]);

  const filteredProjects = useMemo(() => {
    if (!showSuggestions) return [];
    return projects
      .filter((p) => p.name.toLowerCase().includes(currentQuery))
      .slice(0, 8); // Limit results for better UI
  }, [projects, currentQuery, showSuggestions]);

  // 2. The Parser (Runs on every keystroke, but it's very fast)
  const parsed = useMemo(() => parseTaskInput(inputValue, projects), [inputValue, projects]);
  const activeProjectId = parsed.projectId || defaultProjectId;

  // 3. Selection Logic
  const selectProject = (projectName: string) => {
    const lastHashIndex = inputValue.lastIndexOf("#");
    if (lastHashIndex !== -1) {
      const prefix = inputValue.substring(0, lastHashIndex);
      setInputValue(`${prefix}#${projectName} `);
    }
    setShowSuggestions(false);
    setActiveIndex(0);
    // Keep focus on input
    inputRef.current?.focus();
  };

  // 4. Keyboard Navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && filteredProjects.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % filteredProjects.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + filteredProjects.length) % filteredProjects.length);
      } else if (e.key === "Enter" || e.key === "Tab") {
        // If the current query exactly matches the top suggestion, 
        // let Enter submit the form instead of "selecting" it again.
        const currentWord = inputValue.split("#").pop()?.toLowerCase() || "";
        const topMatch = filteredProjects[activeIndex].name.toLowerCase();

        if (currentWord !== topMatch) {
          e.preventDefault();
          selectProject(filteredProjects[activeIndex].name);
        } else {
          // Exact match found and user pressed Enter -> close suggestions and let form submit
          setShowSuggestions(false);
        }
      } else if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    const cursorPosition = e.target.selectionStart || 0;
    setInputValue(val);

    // Find the word the cursor is currently in
    const textBeforeCursor = val.substring(0, cursorPosition);
    const words = textBeforeCursor.split(/\s/);
    const lastWord = words[words.length - 1];

    if (lastWord.startsWith("#")) {
      setShowSuggestions(true);
      setActiveIndex(0); // Reset to top of list when typing starts
    } else {
      setShowSuggestions(false);
    }
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (showSuggestions) return; // Prevent submission if picking a project
    if (!parsed.title || loading) return;

    setLoading(true);
    try {
      console.log(parsed)
      const newTask = await createTaskAction({
        title: parsed.title,
        project_ids: activeProjectId ? [activeProjectId] : [],
        assigned_date: parsed.assignedDate,
        hard_deadline: parsed.hardDeadline,
        scheduled_start: parsed.scheduledStart,
        status: "todo",
      });

      setInputValue("");
      if (showToast) {
        toast.success("Task created", {
          description: `"${parsed.title}" added successfully.`,
          action: { label: "Undo", onClick: () => deleteTaskAction(newTask.id) }
        });
      }
      router.refresh();
    } catch (error) {
      if (showToast) toast.error("Failed to create task");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full group">
      <form onSubmit={handleSubmit} className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Plus className="h-4 w-4 text-muted-foreground" />}
        </div>

        <Input
          ref={inputRef}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Task name... #project @date at time"
          className="pl-10 pr-32 h-11 bg-background border-dashed focus:border-solid transition-all"
          disabled={loading}
          autoFocus
        />

        {/* Floating Badges (Visual confirmation) */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
          {/* Hard Deadline Badge */}
          {parsed.hardDeadline && (
            <div className="flex items-center text-[10px] bg-red-50 text-red-600 border border-red-200 px-1.5 py-0.5 rounded shadow-sm">
              <span className="font-bold mr-1">Due:</span>
              {format(new Date(parsed.hardDeadline), "MMM d")}
            </div>
          )}

          {/* Scheduled Start Badge */}
          {parsed.scheduledStart && (
            <div className="flex items-center text-[10px] bg-purple-50 text-purple-600 border border-purple-200 px-1.5 py-0.5 rounded shadow-sm">
              <span className="font-bold mr-1">At:</span>
              {format(new Date(parsed.scheduledStart), "h:mm a")}
            </div>
          )}

          {/* Assigned Date Badge */}
          {parsed.assignedDate && !parsed.hardDeadline && (
            <div className="flex items-center text-[10px] bg-blue-50 text-blue-600 border border-blue-200 px-1.5 py-0.5 rounded shadow-sm">
              <Calendar className="h-3 w-3 mr-1" />
              {parsed.assignedDate}
            </div>
          )}

          {activeProjectId && (
            <div className="flex items-center text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded shadow-sm">
              <Hash className="h-3 w-3 mr-0.5" />
              {projects.find(p => p.id === activeProjectId)?.name.split(' ')[0]}
            </div>
          )}
        </div>
      </form>

      {/* Suggestion Popover */}
      {showSuggestions && filteredProjects.length > 0 && (
        <div className={cn(
          "absolute z-50 w-full max-w-[300px] bg-popover border rounded-lg shadow-xl p-1 animate-in fade-in zoom-in-95 duration-100",
          popupDirection === "above" ? "mb-2 bottom-full" : "mt-2"
        )}>
          <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            Matching Projects
          </div>
          {filteredProjects.map((project, index) => (
            <button
              key={project.id}
              onClick={() => selectProject(project.name)}
              onMouseEnter={() => setActiveIndex(index)}
              className={cn(
                "w-full text-left px-3 py-2 text-sm rounded-md flex items-center justify-between transition-colors",
                index === activeIndex ? "bg-accent text-accent-foreground" : "bg-transparent"
              )}
            >
              <div className="flex items-center">
                <Hash className={cn("h-3.5 w-3.5 mr-2", index === activeIndex ? "text-primary" : "text-muted-foreground")} />
                {project.name}
              </div>
              {index === activeIndex && <Check className="h-3.5 w-3.5 opacity-50" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
