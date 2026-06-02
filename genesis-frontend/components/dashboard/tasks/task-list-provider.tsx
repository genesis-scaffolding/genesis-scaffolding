"use client";

import * as React from "react";
import { useOptimistic } from "react";
import { Task, Project, Status } from "@/types/productivity";

/**
 * Discriminated union of optimistic updates that can be applied to the task
 * list. Add new variants here when introducing new optimistic actions so the
 * context API stays type-safe and the reducer remains exhaustive.
 */
export type TaskOptimisticAction =
  | { type: "status"; taskId: number; status: Status }
  | { type: "create"; task: Task };

interface TaskListContextValue {
  /**
   * The current optimistic task list. Components that render the list should
   * read this in preference to any prop they were passed, so the optimistic
   * layer is the single source of truth.
   */
  optimisticTasks: Task[];
  /**
   * Dispatch an optimistic update. Must be called from inside a transition
   * (e.g. startTransition) so React can revert the state when the transition
   * completes without a new prop arriving.
   */
  addOptimistic: (action: TaskOptimisticAction) => void;
}

const NOOP_ADD: TaskListContextValue["addOptimistic"] = () => {};

/**
 * Default context. Used when a consumer renders outside of a
 * TaskListProvider (e.g. isolated tests, the floating QuickAddTask on the
 * dashboard layout, or any future page that wants to skip the optimistic
 * layer). In that case dispatches are silently dropped and the page relies
 * on router.refresh() to reconcile.
 */
const defaultContextValue: TaskListContextValue = {
  optimisticTasks: [],
  addOptimistic: NOOP_ADD,
};

export const TaskListContext = React.createContext<TaskListContextValue>(defaultContextValue);

/**
 * A boolean marker set to true inside a TaskListProvider. Consumers use this
 * to distinguish "no provider at all" from "provider present with an empty
 * list" without changing the public TaskListContext shape. The default is
 * false, so any subtree that is not explicitly inside a TaskListProvider
 * sees false here.
 */
export const TaskListProviderActive = React.createContext<boolean>(false);

function optimisticReducer(state: Task[], action: TaskOptimisticAction): Task[] {
  switch (action.type) {
    case "status":
      return state.map((t) =>
        t.id === action.taskId ? { ...t, status: action.status } : t
      );
    case "create":
      // Place the new task at the top of the list so the user can see what
      // they just created. De-dup by id defensively in case the same create
      // is dispatched twice in rapid succession.
      return [action.task, ...state.filter((t) => t.id !== action.task.id)];
    default:
      return state;
  }
}

interface TaskListProviderProps {
  /** The server-rendered task list. The base state for the optimistic layer. */
  tasks: Task[];
  /**
   * Projects, accepted for API symmetry with TaskTable. Not used by the
   * provider today; future optimistic variants (e.g. project rename) can
   * read it from context without changing the provider signature.
   */
  projects?: Project[];
  children: React.ReactNode;
}

/**
 * Owns the optimistic task list for a page. Wrap the TaskTable and any
 * QuickAddTask on the same page in this provider so they share the same
 * optimistic state. The provider renders no DOM; it is purely a state owner.
 */
export function TaskListProvider({ tasks, children }: TaskListProviderProps) {
  const [optimisticTasks, addOptimistic] = useOptimistic(tasks, optimisticReducer);

  const value = React.useMemo<TaskListContextValue>(
    () => ({ optimisticTasks, addOptimistic }),
    [optimisticTasks]
  );

  return (
    <TaskListProviderActive.Provider value={true}>
      <TaskListContext.Provider value={value}>{children}</TaskListContext.Provider>
    </TaskListProviderActive.Provider>
  );
}
