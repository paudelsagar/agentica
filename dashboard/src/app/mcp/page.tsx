"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { Activity, Cpu, Eye, EyeOff, Globe, Link as LinkIcon, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ServerEditState {
  [key: string]: { url: string; auth_token: string; showToken: boolean };
}

export default function MCPPage() {
  const [servers, setServers] = useState<any[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newServer, setNewServer] = useState({ name: "", type: "sse", url: "", auth_token: "" });
  const [isLoading, setIsLoading] = useState(true);
  const [editState, setEditState] = useState<ServerEditState>({});

  const fetchServers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getMCPServers();
      const serverList = Object.values(data) as any[];
      setServers(serverList);
      // Initialize edit state for each server
      const initState: ServerEditState = {};
      serverList.forEach((server: any) => {
        initState[server.name] = {
          url: server.url || "",
          auth_token: server.auth_token || "",
          showToken: false,
        };
      });
      setEditState(initState);
    } catch (error) {
      console.error("Failed to fetch MCP servers:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleAdd = async () => {
    await api.addMCPServer(newServer);
    setIsModalOpen(false);
    setNewServer({ name: "", type: "sse", url: "", auth_token: "" });
    fetchServers();
  };

  const handleUpdate = async (server: any) => {
    const edit = editState[server.name];
    await api.addMCPServer({
      name: server.name,
      type: server.type,
      url: edit.url,
      auth_token: edit.auth_token,
    });
    fetchServers();
  };

  const handleDelete = async (name: string) => {
    if (confirm(`Remove MCP server ${name}?`)) {
      await api.deleteMCPServer(name);
      fetchServers();
    }
  };

  return (
    <div className="p-8 space-y-8 bg-background min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">MCP Servers</h1>
          <p className="text-foreground/60 mt-1">Connect external tools and knowledge bases via Model Context Protocol.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all active:scale-95"
        >
          <Plus className="h-5 w-5" />
          Register Server
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2].map(i => (
            <div key={i} className="h-48 rounded-2xl bg-accent/20 animate-pulse border border-border" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {servers.map((server) => (
            <div key={server.name} className="agent-card group bg-card border border-border shadow-sm hover:bg-accent/5 transition-all">
              <div className="absolute top-0 right-0 p-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={() => handleUpdate(server)}
                  className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 transition-colors"
                  title="Save changes"
                >
                  <Save className="h-4 w-4" />
                </button>
                <button 
                  onClick={() => handleDelete(server.name)}
                  className="p-2 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shadow-inner text-indigo-500">
                  <Cpu className="h-6 w-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-foreground truncate">{server.name}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={cn(
                      "px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider",
                      server.type === "sse" ? "bg-blue-500/10 text-blue-500 border border-blue-500/20" : "bg-purple-500/10 text-purple-500 border border-purple-500/20"
                    )}>
                      {server.type}
                    </span>
                    <div className="flex items-center gap-1.5 text-emerald-500">
                      <Activity className="h-3 w-3 animate-pulse" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Active</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {/* Editable URL */}
                <div className="flex items-center gap-2">
                  <LinkIcon className="h-3.5 w-3.5 text-foreground/40 shrink-0" />
                  <input
                    type="text"
                    value={editState[server.name]?.url || ""}
                    onChange={(e) => setEditState({
                      ...editState,
                      [server.name]: { ...editState[server.name], url: e.target.value }
                    })}
                    className="flex-1 bg-accent/20 border border-border rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:border-indigo-500/50 focus:ring-0 transition-all"
                    placeholder="Endpoint URL"
                  />
                </div>
                
                {/* Editable Token with show/hide */}
                <div className="flex items-center gap-2">
                  <Globe className="h-3.5 w-3.5 text-foreground/40 shrink-0" />
                  <input
                    type={editState[server.name]?.showToken ? "text" : "password"}
                    value={editState[server.name]?.auth_token || ""}
                    onChange={(e) => setEditState({
                      ...editState,
                      [server.name]: { ...editState[server.name], auth_token: e.target.value }
                    })}
                    className="flex-1 bg-accent/20 border border-border rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:border-indigo-500/50 focus:ring-0 transition-all"
                    placeholder="API Token (optional)"
                  />
                  <button
                    onClick={() => setEditState({
                      ...editState,
                      [server.name]: { ...editState[server.name], showToken: !editState[server.name]?.showToken }
                    })}
                    className="p-1.5 rounded-lg bg-accent/30 text-foreground/60 hover:bg-accent/50 transition-colors"
                    title={editState[server.name]?.showToken ? "Hide token" : "Show token"}
                  >
                    {editState[server.name]?.showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-foreground">Register MCP Server</h2>
                <button onClick={() => setIsModalOpen(false)} className="text-foreground/40 hover:text-foreground transition-colors">✕</button>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">Server Identifier</label>
                  <input 
                    type="text" 
                    value={newServer.name}
                    onChange={e => setNewServer({...newServer, name: e.target.value})}
                    placeholder="e.g. WeatherTools"
                    className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">Connection Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    {["sse", "toolbox"].map(type => (
                      <button
                        key={type}
                        onClick={() => setNewServer({...newServer, type})}
                        className={cn(
                          "px-4 py-3 rounded-xl border font-semibold transition-all uppercase tracking-wider text-xs",
                          newServer.type === type 
                            ? "bg-indigo-500/10 border-indigo-500/50 text-indigo-500" 
                            : "bg-accent/20 border-border text-foreground/40 hover:bg-accent/30"
                        )}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">Endpoint URL</label>
                  <input 
                    type="text" 
                    value={newServer.url}
                    onChange={e => setNewServer({...newServer, url: e.target.value})}
                    placeholder="http://localhost:1234/sse"
                    className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">API Token (optional)</label>
                  <input 
                    type="password" 
                    value={newServer.auth_token}
                    onChange={e => setNewServer({...newServer, auth_token: e.target.value})}
                    placeholder="Bearer token or API key"
                    className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="px-6 py-2.5 rounded-xl border border-border text-foreground font-medium hover:bg-accent transition-all"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleAdd}
                  disabled={!newServer.name || !newServer.url}
                  className="px-8 py-2.5 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
                >
                  Register Server
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
