'use client';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Job } from '@/lib/api';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { useRef } from 'react';

interface Props {
  jobs: Job[];
  selectedJob: Job | null;
  onSelectJob: (job: Job) => void;
  onUpload: (file: File) => void;
  loading: boolean;
}

export function DocumentList({ jobs, selectedJob, onSelectJob, onUpload, loading }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <aside className="w-1/4 flex-shrink-0 bg-slate-50 dark:bg-slate-900 flex flex-col border-r">
      <div className="flex h-16 items-center px-6 border-b">
        <div>
          <h1 className="text-lg font-semibold">Kāraka KG</h1>
          <p className="text-xs text-muted-foreground">Knowledge Graph</p>
        </div>
      </div>
      
      <div className="p-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt"
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          className="w-full"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mr-2 h-4 w-4" />
          New Upload
        </Button>
      </div>

      <ScrollArea className="flex-1 px-4">
        <div className="space-y-1">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No documents yet</p>
          ) : (
            jobs.map((job) => (
              <button
                key={job.job_id}
                onClick={() => onSelectJob(job)}
                className={`w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  selectedJob?.job_id === job.job_id
                    ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-200'
                    : 'hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {job.status === 'processing_kg' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileText className="h-4 w-4" />
                )}
                <span className="truncate">{job.filename}</span>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </aside>
  );
}
