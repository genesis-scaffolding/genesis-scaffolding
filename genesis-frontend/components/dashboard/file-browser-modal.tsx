'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getFilesAction, uploadFileAction } from '@/app/actions/sandbox';
import { SandboxFile, ALLOWED_EXTENSIONS } from '@/types/sandbox';
import { Button } from "@/components/ui/button";
import { FileText, Upload, Search, Check, Loader2, HardDrive } from "lucide-react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";

interface FileBrowserModalProps {
  onSelect: (file: SandboxFile) => void;
  currentValue?: string;
  trigger?: React.ReactNode;
}

export function FileBrowserModal({ onSelect, currentValue, trigger }: FileBrowserModalProps) {
  const [files, setFiles] = useState<SandboxFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (open) fetchFiles();
  }, [open]);

  async function fetchFiles() {
    setLoading(true);
    try {
      const data = await getFilesAction();
      // Filter for PDF and Text/Markdown
      const filtered = data.filter(f =>
        ALLOWED_EXTENSIONS.some(ext => f.name.toLowerCase().endsWith(ext))
      );
      setFiles(filtered);
    } catch (err) {
      toast.error("Failed to load sandbox files");
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const newFile = await uploadFileAction(formData);
      toast.success("Uploaded successfully");
      onSelect(newFile);
      setOpen(false);
    } catch (err: any) {
      toast.error(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const filteredFiles = files.filter(f =>
    f.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || <Button variant="outline">Browse Sandbox</Button>}
      </DialogTrigger>
      <DialogContent className="max-w-2xl h-[85vh] flex flex-col p-0 overflow-hidden border-none shadow-2xl">
        <div className="p-6 pb-4 border-b">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Sandbox File Picker
            </DialogTitle>
          </DialogHeader>
        </div>

        <Tabs defaultValue="browse" className="flex-1 flex flex-col min-h-0 bg-slate-50/30">
          <div className="px-6 pt-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="browse">Browse Files</TabsTrigger>
              <TabsTrigger value="upload">Upload New</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="browse" className="flex-1 flex flex-col gap-4 mt-4 px-6 pb-6 overflow-hidden min-h-0">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search files..."
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex-1 min-h-0 border rounded-md">
              <ScrollArea className="h-full w-full">
                {loading ? (
                  <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin" /></div>
                ) : filteredFiles.length === 0 ? (
                  <div className="text-center py-10 text-muted-foreground">No matching files found.</div>
                ) : (
                  <div className="grid gap-2">
                    {filteredFiles.map((file) => {
                      const lastSlash = file.relative_path.lastIndexOf('/');
                      const folderDisplay = lastSlash > 0 ? file.relative_path.substring(0, lastSlash) : 'root';
                      return (
                        <button
                          key={file.relative_path}
                          onClick={() => { onSelect(file); setOpen(false); }}
                          className={`flex items-center justify-between p-3 rounded-lg border text-left transition-colors hover:bg-slate-50 ${currentValue === file.relative_path ? 'border-primary bg-primary/5' : ''}`}
                        >
                          <div className="flex items-center gap-3 overflow-hidden">
                            <FileText className={`h-4 w-4 ${file.name.endsWith('.pdf') ? 'text-red-500' : 'text-blue-500'}`} />
                            <div className="flex flex-col overflow-hidden">
                              <span className="text-sm font-medium truncate">{file.name}</span>
                              <span className="text-xs text-muted-foreground truncate">{folderDisplay}/</span>
                            </div>
                          </div>
                          {currentValue === file.relative_path && <Check className="h-4 w-4 text-primary" />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </div>
          </TabsContent>

          <TabsContent
            value="upload"
            className="flex-1 p-6 flex flex-col min-h-0 ring-0 focus-visible:ring-0"
          >
            <div className="flex-1 border-2 border-dashed border-slate-300 rounded-2xl bg-white hover:bg-slate-50/50 hover:border-primary/40 transition-all flex flex-col items-center justify-center p-8 gap-6 text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center shadow-inner">
                {uploading ? <Loader2 className="h-8 w-8 animate-spin text-primary" /> : <Upload className="h-8 w-8 text-primary" />}
              </div>

              <div className="space-y-2 max-w-[280px]">
                <h3 className="text-lg font-bold text-slate-900">Upload new assets</h3>
                <p className="text-sm text-muted-foreground">
                  Drop your PDFs or Markdown files here. They will be added to your <span className="font-mono text-primary">root/</span> directory.
                </p>
              </div>

              <div className="flex flex-col items-center gap-3">
                <Input
                  type="file"
                  accept=".pdf,.txt,.md"
                  className="hidden"
                  id="file-upload"
                  onChange={handleFileUpload}
                  disabled={uploading}
                />
                <Button
                  asChild
                  disabled={uploading}
                  size="lg"
                  className="px-8 shadow-md hover:shadow-lg transition-all"
                >
                  <label htmlFor="file-upload" className="cursor-pointer">
                    Select File from Computer
                  </label>
                </Button>
                <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">Supports PDF, TXT, MD</span>
              </div>
            </div>
          </TabsContent>

        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
