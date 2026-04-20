'use client'

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { InlineEditForm } from '@/components/ui/inline-edit-form';
import { updateJournalAction } from '@/app/actions/productivity';

interface JournalContentEditorProps {
  journalId: string;
  initialContent: string;
}

export function JournalContentEditor({ journalId, initialContent }: JournalContentEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleConfirm = async (newContent: string) => {
    setLoading(true);
    try {
      await updateJournalAction(journalId, { content: newContent });
      router.refresh();
      setIsEditing(false);
    } finally {
      setLoading(false);
    }
  };

  if (isEditing) {
    return (
      <InlineEditForm
        value={initialContent}
        onConfirm={handleConfirm}
        onCancel={() => setIsEditing(false)}
        loading={loading}
        multiline={true}
        minHeight="800px"
      />
    );
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="prose prose-slate dark:prose-invert max-w-none lg:prose-lg cursor-text hover:bg-muted/10 rounded-lg p-4 -m-4 transition-colors"
    >
      <ReactMarkdown>{initialContent}</ReactMarkdown>
    </div>
  );
}
