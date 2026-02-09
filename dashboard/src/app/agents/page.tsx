"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { Cpu, Edit2, Plus, Settings2, Shield, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAgents();
      setAgents(Object.values(data));
    } catch (error) {
      console.error("Failed to fetch agents:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleDelete = async (name: string) => {
    if (confirm(`Are you sure you want to delete ${name}?`)) {
      await api.deleteAgent(name);
      fetchAgents();
    }
  };

  const openEditModal = (agent: any) => {
    setCurrentAgent(agent);
    setIsModalOpen(true);
  };

  const openCreateModal = () => {
    setCurrentAgent({
      name: "",
      role: "",
      system_prompt: "",
      model_provider: "google",
      model_tier: "fast",
      capabilities: []
    });
    setIsModalOpen(true);
  };

  return (
    <div className="p-8 space-y-8 bg-background min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Agents</h1>
          <p className="text-foreground/60 mt-1">Manage your multi-agent workforce and their specialized roles.</p>
        </div>
        <button 
          onClick={openCreateModal}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all active:scale-95"
        >
          <Plus className="h-5 w-5" />
          Deploy New Agent
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <div key={i} className="h-64 rounded-2xl bg-accent/20 animate-pulse border border-border" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div key={agent.name} className="agent-card group bg-card/40 border border-border hover:bg-accent/10 transition-all">
              <div className="absolute top-0 right-0 p-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={() => openEditModal(agent)}
                  className="p-2 rounded-lg bg-accent text-foreground hover:bg-accent/80 transition-colors"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                <button 
                  onClick={() => handleDelete(agent.name)}
                  className="p-2 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shadow-inner">
                  <Shield className="h-6 w-6 text-indigo-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-foreground leading-tight">{agent.name}</h3>
                  <p className="text-sm font-medium text-emerald-500 mt-0.5 uppercase tracking-wider">{agent.role}</p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div className="rounded-lg bg-accent/30 p-4 border border-border">
                  <p className="text-sm text-foreground/60 line-clamp-3 italic">
                    {agent.system_prompt || "No system prompt defined."}
                  </p>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-foreground/40">
                    <Cpu className="h-3.5 w-3.5" />
                    <span>{agent.model_provider} • {agent.model_tier}</span>
                  </div>
                  <div className="flex items-center gap-2 text-indigo-500">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>{agent.capabilities?.length || 0} Tools</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Basic Modal Implementation */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-foreground flex items-center gap-3">
                  <Settings2 className="h-6 w-6 text-indigo-500" />
                  {currentAgent?.name ? "Update Agent" : "Create Agent"}
                </h2>
                <button onClick={() => setIsModalOpen(false)} className="text-foreground/40 hover:text-foreground transition-colors">✕</button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">Agent Name</label>
                  <input 
                    type="text" 
                    value={currentAgent?.name}
                    onChange={e => setCurrentAgent({...currentAgent, name: e.target.value})}
                    disabled={!!currentAgent?.name && !agents.every(a => a.name !== currentAgent.name)}
                    className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">Specialist Role</label>
                  <input 
                    type="text" 
                    value={currentAgent?.role}
                    onChange={e => setCurrentAgent({...currentAgent, role: e.target.value})}
                    placeholder="e.g. Code Reviewer"
                    className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-foreground/40 uppercase tracking-widest">System Prompt</label>
                <textarea 
                  rows={6}
                  value={currentAgent?.system_prompt}
                  onChange={e => setCurrentAgent({...currentAgent, system_prompt: e.target.value})}
                  className="w-full bg-accent/20 border border-border rounded-xl px-4 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="px-6 py-2.5 rounded-xl border border-border text-foreground font-medium hover:bg-accent transition-all"
                >
                  Cancel
                </button>
                <button 
                  onClick={async () => {
                    if (agents.some(a => a.name === currentAgent.name)) {
                      await api.updateAgent(currentAgent.name, currentAgent);
                    } else {
                      await api.createAgent(currentAgent);
                    }
                    setIsModalOpen(false);
                    fetchAgents();
                  }}
                  className="px-8 py-2.5 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all"
                >
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
