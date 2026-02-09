"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { Bot, Loader2, MessageSquare, Send, Trash2, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState(`thread_${Math.random().toString(36).substring(7)}`);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.runWorkflow(threadId, input);
      if (!response.ok) throw new Error("Failed to run workflow");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader available");

      let assistantContent = "";
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        // Clean up SSE prefix/suffix if present
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                assistantContent += parsed.content;
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  const updated = [...prev.slice(0, -1), { ...last, content: assistantContent }];
                  return updated;
                });
              }
            } catch (e) {
              // Not JSON or partial
              assistantContent += data;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                const updated = [...prev.slice(0, -1), { ...last, content: assistantContent }];
                return updated;
              });
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Error: Failed to communicate with Agentica." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    await api.deleteState(threadId);
    setMessages([]);
    setThreadId(`thread_${Math.random().toString(36).substring(7)}`);
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b border-border px-8 bg-background sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-foreground">Main Flow</h1>
          <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 text-xs font-medium border border-indigo-500/20">
            {threadId}
          </span>
        </div>
        <button 
          onClick={clearChat}
          className="flex items-center gap-2 text-sm text-foreground/40 hover:text-destructive transition-colors"
        >
          <Trash2 className="h-4 w-4" />
          Clear Session
        </button>
      </header>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-8 space-y-8"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="h-16 w-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
              <MessageSquare className="h-8 w-8 text-indigo-500" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-foreground">How can I help today?</h3>
              <p className="text-foreground/60 mt-1">Start a conversation with Agentica to coordinate your task.</p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div 
            key={i}
            className={cn(
              "flex gap-4 max-w-4xl mx-auto",
              msg.role === "user" ? "flex-row-reverse" : "flex-row"
            )}
          >
            <div className={cn(
              "h-10 w-10 shrink-0 rounded-xl flex items-center justify-center border",
              msg.role === "user" 
                ? "bg-indigo-600 border-indigo-500 text-white" 
                : "bg-card border-border text-indigo-500 shadow-sm"
            )}>
              {msg.role === "user" ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
            </div>
            <div className={cn(
              "flex flex-col gap-2 max-w-[85%]",
              msg.role === "user" ? "items-end" : "items-start"
            )}>
              <div className={cn(
                "rounded-2xl px-6 py-4 prose prose-invert dark:prose-invert",
                msg.role === "user" 
                  ? "bg-indigo-600 text-white shadow-indigo-500/10" 
                  : "bg-card border border-border text-foreground shadow-sm"
              )}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                {msg.role === "assistant" && !msg.content && isLoading && (
                  <div className="flex items-center gap-2 py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
                    <span className="text-sm italic text-foreground/40">Thinking...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <footer className="p-8 pt-0 bg-background">
        <div className="max-w-4xl mx-auto relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-[22px] blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
          <div className="relative flex items-end gap-2 bg-card border border-border rounded-[20px] p-1.5 focus-within:border-indigo-500/40 transition-all shadow-sm">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Message Agentica..."
              className="flex-1 bg-transparent border-none focus:ring-0 text-foreground placeholder:text-foreground/40 py-3 px-4 resize-none min-h-[50px] max-h-[200px]"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="h-10 w-10 flex items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-all shadow-lg shadow-indigo-500/20"
            >
              {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </button>
          </div>
          <p className="text-[10px] text-center text-foreground/40 mt-3 uppercase tracking-widest font-medium">
            Shift + Enter for new line • Thread persistence active
          </p>
        </div>
      </footer>
    </div>
  );
}
