'use client';

import { useState, useEffect, useRef } from 'react';
import { Job, Query, api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Send, ChevronDown, Loader2 } from 'lucide-react';

interface Props {
  job: Job;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  query?: Query;
}

export function ChatInterface({ job }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const { query_id } = await api.submitQuery(input, job.job_id);
      
      const assistantMessage: Message = {
        id: query_id,
        type: 'assistant',
        content: '',
        query: { query_id, question: input, status: 'processing' },
      };
      setMessages((prev) => [...prev, assistantMessage]);

      const pollQuery = async () => {
        try {
          const queryData = await api.getQueryStatus(query_id);
          
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === query_id
                ? { ...msg, content: queryData.answer || '', query: queryData }
                : msg
            )
          );

          if (queryData.status === 'completed' || queryData.status === 'failed') {
            clearInterval(pollInterval);
            setLoading(false);
          }
        } catch (error) {
          console.error('Failed to poll query:', error);
          clearInterval(pollInterval);
          setLoading(false);
        }
      };

      await pollQuery();
      const pollInterval = setInterval(pollQuery, 2000);
    } catch (error) {
      console.error('Failed to submit query:', error);
      setLoading(false);
    }
  };

  return (
    <div className="flex w-full">
      <main className="w-[40%] flex flex-col border-r">
        <header className="flex h-16 items-center px-6 border-b">
          <h2 className="text-lg font-semibold">Chat with {job.filename}</h2>
        </header>

        <ScrollArea className="flex-1 p-6">
          <div className="flex flex-col gap-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex flex-col items-${msg.type === 'user' ? 'end' : 'start'} gap-2 max-w-md`}>
                  <div
                    className={`text-sm px-4 py-2.5 rounded-2xl ${
                      msg.type === 'user'
                        ? 'bg-primary text-primary-foreground rounded-br-md'
                        : 'bg-slate-100 dark:bg-slate-800 rounded-bl-md'
                    }`}
                  >
                    {msg.query?.status === 'processing' ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Thinking...</span>
                      </div>
                    ) : (
                      <p>{msg.content || 'Unable to generate answer'}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        <div className="px-6 py-4 border-t">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={loading}
            />
            <Button type="submit" disabled={loading}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </main>

      <aside className="w-[35%] flex flex-col">
        <header className="p-6 border-b">
          <h2 className="text-lg font-semibold">Knowledge Reference</h2>
          <p className="text-sm text-muted-foreground">Data from {job.filename}</p>
        </header>

        <ScrollArea className="flex-1 p-6">
          <div className="space-y-6">
            {messages
              .filter((msg) => msg.type === 'assistant' && msg.query?.references)
              .slice(-1)
              .map((msg) => (
                <div key={msg.id} className="space-y-4">
                  {msg.query?.references?.map((ref, i) => (
                    <blockquote key={i} className="border-l-4 pl-4 italic text-muted-foreground">
                      "{ref.sentence}"
                    </blockquote>
                  ))}

                  <Collapsible defaultOpen>
                    <Card>
                      <CollapsibleTrigger className="flex w-full items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-800">
                        <h3 className="text-sm font-medium">Extracted Knowledge Graph</h3>
                        <ChevronDown className="h-4 w-4" />
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="border-t p-4">
                          <pre className="bg-slate-100 dark:bg-slate-900 p-4 rounded-lg text-xs overflow-x-auto">
                            <code>{JSON.stringify({ nodes: [], edges: [] }, null, 2)}</code>
                          </pre>
                        </div>
                      </CollapsibleContent>
                    </Card>
                  </Collapsible>
                </div>
              ))}
          </div>
        </ScrollArea>
      </aside>
    </div>
  );
}
