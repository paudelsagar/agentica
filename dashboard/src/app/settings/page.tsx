"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { RefreshCw, Settings, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const PROVIDERS = ["google", "openai", "anthropic", "xai", "ollama"];
const TIERS = ["fast", "heavy"];

export default function SettingsPage() {
  const [modelConfig, setModelConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const fetchConfig = async () => {
    setIsLoading(true);
    try {
      const data = await api.getModelConfig();
      setModelConfig(data);
    } catch (e) {
      console.error("Failed to fetch model config:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleUpdate = async (provider: string, tier: string, model: string) => {
    setIsSaving(true);
    try {
      await api.updateModelConfig({ provider, tier, model });
      fetchConfig();
    } catch (e) {
      console.error("Update failed:", e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-8 bg-background min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">System Settings</h1>
          <p className="text-foreground/60 mt-1">Configure global model routing and system behavior.</p>
        </div>
        <button 
          onClick={fetchConfig}
          className="flex items-center gap-2 text-sm text-indigo-500 hover:text-indigo-400 transition-colors"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          Sync with Backend
        </button>
      </div>

      <div className="max-w-6xl space-y-12">
        {/* Model Tier Mapping */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <Zap className="h-6 w-6 text-indigo-500" />
            <h2 className="text-xl font-bold text-foreground">Model Tier Mapping</h2>
          </div>
 
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {PROVIDERS.map(provider => (
              <div key={provider} className="p-6 rounded-2xl bg-card border border-border shadow-sm space-y-6">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-500 uppercase font-bold text-xs">
                    {provider[0]}
                  </div>
                  <h3 className="text-lg font-bold text-foreground capitalize">{provider}</h3>
                </div>
 
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {TIERS.map(tier => (
                    <div key={tier} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-[10px] font-bold text-foreground/60 uppercase tracking-widest">{tier} Model</label>
                        <span className={cn(
                          "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded",
                          tier === "fast" ? "text-emerald-500 bg-emerald-500/10" : "text-amber-500 bg-amber-500/10"
                        )}>
                          {tier === "fast" ? "FAST" : "HEAVY"}
                        </span>
                      </div>
                      <div className="relative">
                        <input 
                          type="text"
                          value={modelConfig?.[provider]?.[tier] || ""}
                          onChange={(e) => {
                             const newConfig = { ...modelConfig };
                             if (!newConfig[provider]) newConfig[provider] = {};
                             newConfig[provider][tier] = e.target.value;
                             setModelConfig(newConfig);
                          }}
                          onBlur={() => handleUpdate(provider, tier, modelConfig[provider][tier])}
                          className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all font-mono text-sm shadow-sm"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
 
        {/* System Info */}
        <section className="space-y-6 p-8 rounded-2xl bg-card border border-border shadow-sm">
          <div className="flex items-center gap-3">
            <Settings className="h-6 w-6 text-indigo-500" />
            <h2 className="text-xl font-bold text-foreground">General Information</h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            <div>
               <p className="text-xs font-bold text-foreground/40 uppercase tracking-widest mb-1">Backend Connectivity</p>
               <p className="text-foreground font-medium">WebSocket & REST Active</p>
            </div>
            <div>
               <p className="text-xs font-bold text-foreground/40 uppercase tracking-widest mb-1">State Persistence</p>
               <p className="text-foreground font-medium">SQLite (state.db)</p>
            </div>
            <div>
               <p className="text-xs font-bold text-foreground/40 uppercase tracking-widest mb-1">Configuration Storage</p>
               <p className="text-foreground font-medium">SQLite (agentica_config.db)</p>
            </div>
            <div>
               <p className="text-xs font-bold text-foreground/40 uppercase tracking-widest mb-1">Environment</p>
               <p className="text-foreground font-medium">Production Orchestrator</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
