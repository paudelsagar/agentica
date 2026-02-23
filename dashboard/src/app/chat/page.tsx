"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { Bot, Brain, Check, ChevronLeft, ChevronRight, ChevronUp, Edit2, Globe, Loader2, MessageSquare, Plus, Send, Trash2, User } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Filter agent content to remove technical markers from all agent responses
// Handles multiple formats:
// - "SUMMARY: text [END_SUMMARY] PLAN:..." -> extracts "text"
// - "I'll check... [END_SUMMARY] PLAN:..." -> extracts "I'll check..."
// - "text PLAN: ..." -> extracts "text"
function filterAgentContent(content: string): string {
  let filtered = content;
  
  // If SUMMARY: exists, extract content after it
  const summaryMatch = filtered.toUpperCase().indexOf("SUMMARY:");
  if (summaryMatch !== -1) {
    const afterPrefix = filtered.substring(summaryMatch + 8);
    // If it starts with a colon and space or just a colon, handle it
    filtered = afterPrefix.trimStart();
  }
  
  // Find the earliest technical marker and cut there
  const markers = [
    "[END_SUMMARY]", 
    "PLAN:", 
    "NEXT AGENT:", 
    "DELEGATION:", 
    "```tool_code",
    "I am sorry, I am unable to save",  // Error messages from failed tool calls
    "MemoryAgent",  // Internal agent names in responses
  ];
  let endIdx = filtered.length;
  for (const marker of markers) {
    const idx = marker === "```tool_code" 
      ? filtered.indexOf(marker)
      : filtered.toUpperCase().indexOf(marker.toUpperCase());
    if (idx !== -1) {
      endIdx = Math.min(endIdx, idx);
    }
  }
  
  return filtered.substring(0, endIdx).trim();
}

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

interface Session {
  thread_id: string;
  agent: string;
  preview: string;
  success: boolean;
  timestamp: string;
  custom_name?: string;
}

function SearchParamsHandler({ 
  activeThreadId, 
  loadThread, 
  setActiveThreadId, 
  setMessages 
}: { 
  activeThreadId: string | null;
  loadThread: (tid: string, push: boolean) => void;
  setActiveThreadId: (id: string | null) => void;
  setMessages: (m: Message[]) => void;
}) {
  const searchParams = useSearchParams();
  
  useEffect(() => {
    const threadParam = searchParams.get("thread");
    if (threadParam && threadParam !== activeThreadId) {
      loadThread(threadParam, false);
    } else if (!threadParam && activeThreadId) {
      setActiveThreadId(null);
      setMessages([]);
    }
  }, [searchParams, activeThreadId, loadThread, setActiveThreadId, setMessages]);

  return null;
}

function ChatInterface() {
  const router = useRouter();
  const pathname = usePathname();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingMode, setThinkingMode] = useState(false);
  const [webSearch, setWebSearch] = useState(true);
  const [isSessionsLoading, setIsSessionsLoading] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState("");
  const [streamingAgent, setStreamingAgent] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  
  // Initialize state synchronously to avoid flicker
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("chatSidebarOpen");
      if (saved !== null) return saved === "true";
      return window.innerWidth >= 1024;
    }
    return true; // Server-side default
  });

  const [isMounted, setIsMounted] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
    // Remove the pre-hydration class to hand over control to React
    document.documentElement.classList.remove("chat-sidebar-init-collapsed");
  }, []);

  // Persist sidebar state to localStorage
  useEffect(() => {
    localStorage.setItem("chatSidebarOpen", isSidebarOpen.toString());
  }, [isSidebarOpen]);

  // Handle auto-closing on resize (but don't force if user didn't manually toggle)
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Initial load
  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const fetchSessions = async () => {
    setIsSessionsLoading(true);
    try {
      const data = await api.getRecentTrajectories(20);
      setSessions(data);
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    } finally {
      setIsSessionsLoading(false);
    }
  };

  const loadThread = async (threadId: string, pushToRouter: boolean = true) => {
    if (activeThreadId === threadId) return;
    
    setActiveThreadId(threadId);
    setMessages([]);
    setIsLoading(true);
    setHasMore(false);

    if (pushToRouter) {
      const url = new URL(window.location.href);
      url.searchParams.set("thread", threadId);
      router.push(url.pathname + url.search, { scroll: false });
    }

    try {
      const result = await api.getThreadHistory(threadId, 20, 0);
      setMessages(result.messages || []);
      setHasMore(result.hasMore || false);
      // On mobile, close sidebar after selecting a thread
      if (window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      }
    } catch (error) {
      console.error("Failed to load thread history:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMoreMessages = async () => {
    if (!activeThreadId || isLoadingMore || !hasMore) return;
    
    setIsLoadingMore(true);
    const scrollContainer = scrollRef.current;
    const previousScrollHeight = scrollContainer?.scrollHeight || 0;
    
    try {
      const result = await api.getThreadHistory(activeThreadId, 20, messages.length);
      if (result.messages?.length > 0) {
        setMessages((prev) => [...result.messages, ...prev]);
        setHasMore(result.hasMore || false);
        // Maintain scroll position after prepending old messages
        if (scrollContainer) {
          requestAnimationFrame(() => {
            const newScrollHeight = scrollContainer.scrollHeight;
            scrollContainer.scrollTop = newScrollHeight - previousScrollHeight;
          });
        }
      }
    } catch (error) {
      console.error("Failed to load more messages:", error);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const startNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setStreamingAgent(null);
    setIsLoading(false);
    
    // Clear URL params
    const url = new URL(window.location.href);
    url.searchParams.delete("thread");
    router.push(url.pathname, { scroll: false });
    
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const threadId = activeThreadId || `thread_${Math.random().toString(36).substring(7)}`;
    const isNew = !activeThreadId;
    
    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setStreamingAgent("SupervisorAgent");

    // If new thread, update URL and state immediately so the browser reflects the state
    if (isNew) {
      setActiveThreadId(threadId);
      const url = new URL(window.location.href);
      url.searchParams.set("thread", threadId);
      router.replace(url.pathname + url.search, { scroll: false });

      // Optimistic session for sidebar
      const newSession: Session = {
        thread_id: threadId,
        agent: "SupervisorAgent",
        preview: input.substring(0, 50),
        success: true,
        timestamp: new Date().toISOString()
      };
      setSessions((prev) => [newSession, ...prev]);
    }

    try {
      const response = await api.runWorkflow(threadId, input, thinkingMode, webSearch);
      if (!response.ok) throw new Error("Failed to run workflow");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader available");

      let assistantContent = "";
      let hasStarted = false;
      let currentStreamingAgent: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              
              if (parsed.agent) {
                setStreamingAgent(parsed.agent);
              }

              if (parsed.content) {
                // Track content per agent - when agent changes, start a new bubble
                const isNewAgent = parsed.agent && parsed.agent !== currentStreamingAgent;

                if (!hasStarted || isNewAgent) {
                  // Starting new agent bubble
                  hasStarted = true;
                  currentStreamingAgent = parsed.agent || currentStreamingAgent;
                  assistantContent = parsed.content;
                  
                  // Only create bubble if content is non-empty after filtering
                  const filteredContent = filterAgentContent(assistantContent);
                  if (filteredContent.trim()) {
                    setMessages((prev) => [...prev, { role: "assistant", content: filteredContent, agent: currentStreamingAgent || undefined }]);
                  }
                } else {
                  // Continuing existing agent's bubble
                  assistantContent += parsed.content;
                  const filteredContent = filterAgentContent(assistantContent);
                  
                  if (filteredContent.trim()) {
                    setMessages((prev) => {
                      // Find the last message from this agent and update it
                      const lastIdx = prev.length - 1;
                      if (lastIdx >= 0 && prev[lastIdx].role === "assistant" && prev[lastIdx].agent === currentStreamingAgent) {
                        return [...prev.slice(0, lastIdx), { ...prev[lastIdx], content: filteredContent }];
                      } else {
                        // No existing bubble for this agent, create one
                        return [...prev, { role: "assistant", content: filteredContent, agent: currentStreamingAgent || undefined }];
                      }
                    });
                  }
                }
              }
            } catch (e) {
              // Fallback for non-json data
              if (!hasStarted) {
                hasStarted = true;
                setMessages((prev) => [...prev, { role: "assistant", content: data }]);
                assistantContent = data;
              } else {
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
      }
      setStreamingAgent(null);
      fetchSessions();
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Error: Failed to communicate with Agentica." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteSession = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    try {
      await api.deleteState(threadId);
      fetchSessions();
      if (activeThreadId === threadId) {
        startNewChat();
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
    }
  };

  const startRename = (e: React.MouseEvent, session: Session) => {
    e.stopPropagation();
    setEditingSessionId(session.thread_id);
    setEditingSessionName(session.custom_name || session.preview);
  };

  const handleRename = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!editingSessionId || !editingSessionName.trim()) return;

    try {
      await api.renameThread(editingSessionId, editingSessionName.trim());
      setEditingSessionId(null);
      fetchSessions();
    } catch (error) {
      console.error("Failed to rename thread:", error);
    }
  };

  const activeSession = sessions.find(s => s.thread_id === activeThreadId);
  const displayTitle = activeSession?.custom_name || activeSession?.preview || "AI Intelligence Agent";

  // Sync browser tab title
  useEffect(() => {
    if (activeThreadId) {
      document.title = `${displayTitle} | Agentica`;
    } else {
      document.title = `New Chat | Agentica`;
    }
  }, [activeThreadId, displayTitle]);

  return (
    <div 
      className="flex h-screen bg-background overflow-hidden relative"
      suppressHydrationWarning
    >
      <Suspense fallback={null}>
        <SearchParamsHandler 
          activeThreadId={activeThreadId}
          loadThread={loadThread}
          setActiveThreadId={setActiveThreadId}
          setMessages={setMessages}
        />
      </Suspense>

      {/* Pre-hydration script to prevent sidebar flicker */}
      <script
        dangerouslySetInnerHTML={{
          __html: `
            (function() {
              const saved = localStorage.getItem("chatSidebarOpen");
              if (saved === "false" || (saved === null && window.innerWidth < 1024)) {
                document.documentElement.classList.add("chat-sidebar-init-collapsed");
              }
            })();
          `,
        }}
      />
      
      {/* Instant CSS override for pre-hydration state */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
            .chat-sidebar-init-collapsed .chat-sidebar {
              transform: translateX(-100%) !important;
              margin-left: -18rem !important;
              transition: none !important;
            }
            @media (min-width: 1024px) {
              .chat-sidebar-init-collapsed .chat-sidebar {
                margin-left: -18rem !important;
                transform: none !important;
              }
            }
            .chat-sidebar-init-collapsed .sidebar-toggle-btn {
              background-color: transparent !important;
              border-color: var(--color-border) !important;
              color: var(--color-foreground) !important;
            }
          `,
        }}
      />

      {/* Sidebar Overlay (Mobile) */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-background/60 backdrop-blur-sm z-20 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "chat-sidebar fixed inset-y-0 left-0 lg:static z-30 w-72 border-r border-border flex flex-col bg-card shrink-0 ease-in-out h-full",
        isMounted ? "transition-transform duration-300" : "transition-none",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:-ml-72"
      )}>
        <div className="h-20 px-6 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-indigo-500" />
            <h2 className="font-bold text-foreground">Chat History</h2>
          </div>
          <button 
            onClick={startNewChat}
            className="p-1.5 rounded-lg hover:bg-accent text-foreground/60 hover:text-indigo-500 transition-all active:scale-90"
            title="New Thread"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>


        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isSessionsLoading && sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 gap-3 opacity-40">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-xs">Loading history...</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 opacity-40">
              <MessageSquare className="h-8 w-8 mb-2" />
              <p className="text-xs text-center px-4">No conversations yet. Start a new one!</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div key={session.thread_id} className="relative group">
                {editingSessionId === session.thread_id ? (
                  <form 
                    onSubmit={handleRename}
                    className="flex items-center gap-2 p-2 bg-accent rounded-xl ring-1 ring-indigo-500/50"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      autoFocus
                      className="flex-1 bg-transparent text-sm font-medium outline-none px-1"
                      value={editingSessionName}
                      onChange={(e) => setEditingSessionName(e.target.value)}
                      onBlur={() => handleRename()}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') setEditingSessionId(null);
                      }}
                    />
                    <button type="submit" className="p-1 hover:text-indigo-500">
                      <Check className="h-4 w-4" />
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      onClick={() => loadThread(session.thread_id)}
                      className={cn(
                        "w-full text-left p-3 rounded-xl transition-all relative pr-10",
                        activeThreadId === session.thread_id
                          ? "bg-indigo-600/10 border-indigo-500/20 ring-1 ring-indigo-500/20"
                          : "hover:bg-accent border-transparent"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2 overflow-hidden">
                        <span className={cn(
                          "block text-sm font-medium truncate",
                          activeThreadId === session.thread_id ? "text-indigo-500" : "text-foreground"
                        )}>
                          {session.custom_name || session.preview || "Untitled Conversation"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-foreground/40 font-mono">
                          {session.agent.split(",")[0]}
                        </span>
                        <span className="text-[10px] text-foreground/40">
                          {new Date(session.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                    </button>
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                      <button
                        onClick={(e) => startRename(e, session)}
                        className="p-1.5 rounded-lg hover:bg-indigo-500/10 text-foreground/20 hover:text-indigo-500"
                        title="Rename thread"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => deleteSession(e, session.thread_id)}
                        className="p-1.5 rounded-lg hover:bg-red-500/10 text-foreground/20 hover:text-red-500"
                        title="Delete thread"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
        
      </aside>

      {/* Border-mounted Toggle Button (Desktop & Tablet) */}
      <div className={cn(
        "hidden lg:flex absolute top-1/2 z-50 transition-all duration-300 -translate-y-1/2",
        isSidebarOpen ? "left-72 -translate-x-1/2" : "left-0 translate-x-0 ml-1.5",
        !isMounted && "opacity-0"
      )}>
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className={cn(
            "h-6 w-6 rounded-full bg-background border border-border flex items-center justify-center shadow-md hover:bg-accent text-foreground/60 hover:text-indigo-500 transition-all hover:scale-110 active:scale-95 group",
            !isSidebarOpen && "border-l-0 rounded-l-none"
          )}
          title={isSidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          {isSidebarOpen ? (
            <ChevronLeft className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      <div className="flex-1 flex flex-col min-w-0 bg-background transition-all duration-300">

        {/* Message Container */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-8 space-y-8 scroll-smooth"
        >
          {messages.length === 0 ? (
            <div className="h-full flex-1 flex flex-col items-center justify-center max-w-md mx-auto text-center space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-1000">
              <div className="w-20 h-20 rounded-3xl bg-indigo-600/10 flex items-center justify-center">
                <MessageSquare className="h-10 w-10 text-indigo-600" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold tracking-tight">How can I help you today?</h2>
                <p className="text-foreground/60 leading-relaxed">
                  Start a new conversation with our multi-agent system. I can help you with analysis, coding, or general questions.
                </p>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-8 pb-4">
              {/* Load More button at the top */}
              {hasMore && (
                <div className="flex justify-center py-4">
                  <button
                    onClick={loadMoreMessages}
                    disabled={isLoadingMore}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground/60 hover:text-foreground bg-accent/30 hover:bg-accent/50 rounded-xl transition-all disabled:opacity-50"
                  >
                    {isLoadingMore ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <ChevronUp className="h-4 w-4" />
                        Load older messages
                      </>
                    )}
                  </button>
                </div>
              )}
              {Array.isArray(messages) && messages.map((message, index) => (
                <div 
                  key={index} 
                  className={cn(
                    "flex gap-4 animate-in fade-in duration-500",
                    message.role === "user" ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <div className={cn(
                    "h-10 w-10 shrink-0 rounded-xl flex items-center justify-center shadow-lg",
                    message.role === "user" 
                      ? "bg-indigo-600 text-white shadow-indigo-500/20" 
                      : "bg-card border border-border shadow-black/5"
                  )}>
                    {message.role === "user" ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5 text-indigo-500" />}
                  </div>
                  <div className={cn(
                    "flex flex-col max-w-[85%] min-w-0 space-y-1.5",
                    message.role === "user" ? "items-end" : "items-start"
                  )}>
                    {message.agent && (
                      <span className="text-[11px] font-bold text-indigo-500 uppercase tracking-widest px-1">
                        {message.agent.split(",")[0]}
                      </span>
                    )}
                    <div className={cn(
                      "w-full px-5 py-3.5 rounded-2xl shadow-sm text-sm leading-relaxed overflow-hidden",
                      message.role === "user" 
                        ? "bg-accent text-foreground rounded-tr-none border border-border" 
                        : "bg-card border border-border text-foreground rounded-tl-none"
                    )}>
                      <div className="prose dark:prose-invert prose-sm break-words overflow-x-auto max-w-none w-full">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-4 animate-pulse">
                  <div className="h-10 w-10 rounded-xl bg-card border border-border flex items-center justify-center">
                    <Bot className="h-5 w-5 text-indigo-500/50" />
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="bg-card border border-border rounded-2xl rounded-tl-none px-6 py-4 flex gap-2">
                      <div className="h-2 w-2 rounded-full bg-indigo-500/40 animate-bounce [animation-delay:-0.3s]" />
                      <div className="h-2 w-2 rounded-full bg-indigo-500/40 animate-bounce [animation-delay:-0.15s]" />
                      <div className="h-2 w-2 rounded-full bg-indigo-500/40 animate-bounce" />
                    </div>
                    {streamingAgent && (
                      <span className="text-[10px] font-bold text-indigo-500/60 uppercase tracking-widest px-1 animate-pulse">
                        {streamingAgent} is thinking...
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input */}
        <footer className="p-4 md:p-8 pt-0 bg-background/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto flex flex-col gap-3">
            {/* Toggles */}
            <div className="flex items-center gap-2 px-1">
              <button
                onClick={() => setThinkingMode(!thinkingMode)}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all border",
                  thinkingMode 
                    ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400" 
                    : "bg-muted/50 border-border text-foreground/50 hover:text-foreground/70"
                )}
              >
                <Brain className={cn("h-3.5 w-3.5", thinkingMode && "animate-pulse")} />
                Thinking Mode
              </button>
              <button
                onClick={() => setWebSearch(!webSearch)}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all border",
                  webSearch 
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                    : "bg-muted/50 border-border text-foreground/50 hover:text-foreground/70"
                )}
              >
                <Globe className="h-3.5 w-3.5" />
                Web Search
              </button>
            </div>

            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-[24px] blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
              <div className="relative flex items-end gap-2 bg-card border border-border rounded-[22px] p-2 focus-within:border-indigo-500/40 focus-within:ring-2 focus-within:ring-indigo-500/10 transition-all shadow-xl shadow-indigo-500/5">
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
                className="flex-1 bg-transparent border-none outline-none focus:ring-0 focus:outline-none text-foreground placeholder:text-foreground/40 py-3 px-4 resize-none min-h-[50px] max-h-[200px]"
              />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  className="h-12 w-12 flex items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
                >
                  {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return <ChatInterface />;
}
