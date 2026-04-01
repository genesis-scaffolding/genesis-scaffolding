"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Loader2, Save, Brain } from "lucide-react";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { EventLog, TopicalMemory } from "@/types/memory";
import { getMemoryTagsAction, createEventAction, updateEventAction, createTopicAction, updateTopicAction } from "@/app/actions/memory";

const memorySchema = z.object({
  subject: z.string().optional(),
  content: z.string().min(1, "Content is required"),
  tags: z.string().optional(), // Comma-separated string for input
  importance: z.number().min(1).max(5),
  event_time: z.string().optional(), // For events only
});

type MemoryFormValues = z.infer<typeof memorySchema>;

interface MemoryFormProps {
  memoryType: "event" | "topic";
  initialData?: EventLog | TopicalMemory;
}

export function MemoryForm({ memoryType, initialData }: MemoryFormProps) {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const [existingTags, setExistingTags] = useState<Record<string, number>>({});
  const [tagInput, setTagInput] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>(initialData?.tags || []);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const isEditMode = !!initialData;
  const isEvent = memoryType === "event";

  const form = useForm<MemoryFormValues>({
    resolver: zodResolver(memorySchema),
    defaultValues: {
      subject: initialData?.subject || "",
      content: initialData?.content || "",
      tags: initialData?.tags?.join(", ") || "",
      importance: initialData?.importance || 3,
      event_time: isEvent && initialData ? (initialData as EventLog).event_time : "",
    },
  });

  useEffect(() => {
    async function fetchTags() {
      try {
        const tagData = await getMemoryTagsAction();
        setExistingTags(tagData.tag_counts);
      } catch (error) {
        console.error("Failed to fetch tags:", error);
      }
    }
    fetchTags();
  }, []);

  const filteredSuggestions = Object.entries(existingTags)
    .filter(([tag]) =>
      tag.toLowerCase().includes(tagInput.toLowerCase()) &&
      !selectedTags.includes(tag)
    )
    .sort((a, b) => b[1] - a[1]) // Sort by count descending
    .slice(0, 5);

  function handleTagInput(keyDown: React.KeyboardEvent<HTMLInputElement>) {
    if (keyDown.key === "Enter" || keyDown.key === ",") {
      keyDown.preventDefault();
      const value = tagInput.trim();
      if (value && !selectedTags.includes(value)) {
        setSelectedTags([...selectedTags, value]);
        setTagInput("");
      }
    } else if (keyDown.key === "Backspace" && !tagInput && selectedTags.length > 0) {
      setSelectedTags(selectedTags.slice(0, -1));
    }
  }

  function addTag(tag: string) {
    if (!selectedTags.includes(tag)) {
      setSelectedTags([...selectedTags, tag]);
    }
    setTagInput("");
    setShowSuggestions(false);
  }

  function removeTag(tag: string) {
    setSelectedTags(selectedTags.filter(t => t !== tag));
  }

  async function onSubmit(values: MemoryFormValues) {
    setIsPending(true);
    try {
      const payload = {
        subject: values.subject || null,
        content: values.content,
        tags: selectedTags,
        importance: values.importance,
      };

      if (isEvent) {
        if (isEditMode && initialData) {
          await updateEventAction(initialData.id, {
            ...(values.subject !== null && { subject: values.subject }),
            content: values.content,
            tags: selectedTags,
            importance: values.importance,
          });
          toast.success("Event updated successfully!");
        } else {
          await createEventAction({
            event_time: values.event_time || new Date().toISOString(),
            content: values.content,
            tags: selectedTags,
            importance: values.importance,
            related_memory_ids: [],
          });
          toast.success("Event created successfully!");
        }
      } else {
        if (isEditMode && initialData) {
          await updateTopicAction(initialData.id, {
            ...(values.subject !== null && { subject: values.subject }),
            content: values.content,
            tags: selectedTags,
            importance: values.importance,
          });
          toast.success("Topic updated successfully!");
        } else {
          await createTopicAction({
            content: values.content,
            tags: selectedTags,
            importance: values.importance,
          });
          toast.success("Topic created successfully!");
        }
      }

      router.replace('/dashboard/memory');
      router.refresh();
    } catch (error: any) {
      toast.error(error.message);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10 bg-white p-8 rounded-xl border shadow-sm">

        <section className="space-y-6">
          <div className="flex items-center gap-2 text-slate-900">
            <Brain className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold">{isEditMode ? "Edit Memory" : "New Memory"}</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            <FormField
              control={form.control}
              name="subject"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Subject</FormLabel>
                  <FormControl>
                    <Input placeholder="Optional subject..." {...field} value={field.value || ""} />
                  </FormControl>
                  <FormDescription className="text-[10px]">A brief label for this memory</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {isEvent && (
              <FormField
                control={form.control}
                name="event_time"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Event Time</FormLabel>
                    <FormControl>
                      <Input type="datetime-local" {...field} />
                    </FormControl>
                    <FormDescription className="text-[10px]">When did this event occur?</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="importance"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Importance (1-5)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={5}
                      {...field}
                      value={field.value || 3}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 3)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="space-y-2">
            <Label>Tags</Label>
            <div className="relative">
              <Input
                placeholder="Type to add tags (press Enter)..."
                value={tagInput}
                onChange={(e) => {
                  setTagInput(e.target.value);
                  setShowSuggestions(true);
                }}
                onKeyDown={handleTagInput}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              />
              {showSuggestions && filteredSuggestions.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-background border rounded-md shadow-md">
                  {filteredSuggestions.map(([tag, count]) => (
                    <button
                      key={tag}
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-accent flex justify-between"
                      onMouseDown={() => addTag(tag)}
                    >
                      <span>{tag}</span>
                      <span className="text-xs text-muted-foreground">{count}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedTags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {selectedTags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="cursor-pointer" onClick={() => removeTag(tag)}>
                    {tag} ×
                  </Badge>
                ))}
              </div>
            )}
            <FormDescription className="text-[10px]">
              Existing tags are suggested. Click × to remove.
            </FormDescription>
          </div>

          <FormField
            control={form.control}
            name="content"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Content</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="What do you want to remember?"
                    className="min-h-[200px] font-mono text-sm"
                    {...field}
                    value={field.value || ""}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </section>

        <div className="flex justify-end pt-4">
          <Button type="submit" size="lg" className="px-12" disabled={isPending}>
            {isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {isEditMode ? "Save Changes" : "Create Memory"}
          </Button>
        </div>
      </form>
    </Form>
  );
}