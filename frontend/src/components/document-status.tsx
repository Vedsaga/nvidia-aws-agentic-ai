'use client';

import { useEffect, useState } from 'react';
import { Job, api, ProcessingChainEntry } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, Loader2 } from 'lucide-react';

interface Props {
  job: Job;
}

export function DocumentStatus({ job }: Props) {
  const [chain, setChain] = useState<ProcessingChainEntry[]>([]);
  const [currentJob, setCurrentJob] = useState<Job>(job);

  useEffect(() => {
    setCurrentJob(job);
  }, [job]);

  useEffect(() => {
    const loadChain = async () => {
      try {
        const data = await api.getProcessingChain(currentJob.job_id);
        setChain(data.slice(-10));
      } catch (error) {
        console.error('Failed to load chain:', error);
      }
    };

    const loadStatus = async () => {
      try {
        const updated = await api.getJobStatus(currentJob.job_id);
        setCurrentJob(updated);
      } catch (error) {
        console.error('Failed to load status:', error);
      }
    };

    if (currentJob.status === 'processing_kg' || currentJob.status === 'processing') {
      loadChain();
      loadStatus();
      const interval = setInterval(() => {
        loadChain();
        loadStatus();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [currentJob.job_id, currentJob.status]);

  return (
    <main className="w-3/4 flex flex-col h-screen">
      <div className="flex-grow p-6 lg:p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          <header>
            <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              Processing: {currentJob.filename}
              {(currentJob.status === 'processing_kg' || currentJob.status === 'processing') && (
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              )}
            </h2>
          </header>

          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="p-6">
              <p className="text-sm font-medium text-muted-foreground">Status</p>
              <p className="text-2xl font-bold mt-2">{currentJob.status}</p>
            </Card>
            <Card className="p-6">
              <p className="text-sm font-medium text-muted-foreground">Sentences Processed</p>
              <p className="text-2xl font-bold mt-2">
                {currentJob.completed_sentences} / {currentJob.total_sentences}
              </p>
            </Card>
            <Card className="p-6">
              <p className="text-sm font-medium text-muted-foreground">Total LLM Calls</p>
              <p className="text-2xl font-bold mt-2">{currentJob.llm_calls_made}</p>
            </Card>
          </section>

          <section className="flex flex-col gap-3">
            <div className="flex gap-6 justify-between items-center">
              <p className="text-base font-medium">Overall Progress</p>
              <p className="text-sm text-muted-foreground">{currentJob.progress_percentage.toFixed(1)}%</p>
            </div>
            <Progress value={currentJob.progress_percentage} />
          </section>

          {chain.length > 0 && (
            <Collapsible defaultOpen>
              <Card>
                <CollapsibleTrigger className="flex w-full items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                  <p className="text-sm font-medium">Live Processing Chain</p>
                  <ChevronDown className="h-4 w-4 transition-transform" />
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="border-t p-4 max-h-64 overflow-y-auto">
                    <div className="flex flex-col-reverse gap-2 font-mono text-xs">
                      {chain.map((entry, i) => (
                        <p key={i}>
                          <Badge variant="outline" className="mr-2">
                            {entry.stage}
                          </Badge>
                          {entry.duration_ms}ms
                        </p>
                      ))}
                    </div>
                  </div>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}
        </div>
      </div>

      <footer className="p-6 lg:p-8 border-t bg-slate-50/50 dark:bg-slate-900/50">
        <div className="max-w-4xl mx-auto">
          <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-900">
            <div className="flex items-start gap-3">
              <div className="flex flex-col">
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">Chat Disabled</p>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Chat will be enabled once processing is complete.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </footer>
    </main>
  );
}
