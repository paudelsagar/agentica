"use client";

import { api } from "@/lib/api";
import { clsx, type ClassValue } from "clsx";
import { CheckCircle2, Eye, EyeOff, Key, Save, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const secretKeys = [
  { key: "GOOGLE_API_KEY", label: "Google AI (Gemini)", provider: "google" },
  { key: "OPENAI_API_KEY", label: "OpenAI", provider: "openai" },
  { key: "ANTHROPIC_API_KEY", label: "Anthropic", provider: "anthropic" },
  { key: "COHERE_API_KEY", label: "Cohere", provider: "cohere" },
  { key: "TAVILY_API_KEY", label: "Tavily Search", provider: "tavily" },
];

export default function SecretsPage() {
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [serverStatus, setServerStatus] = useState<Record<string, any>>({});
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchSecrets = async () => {
    setIsLoading(true);
    try {
      const data = await api.getSecrets();
      setServerStatus(data);
      // Reset form values on fetch to avoid overwriting with old masking
      setFormValues({});
    } catch (error) {
      console.error("Failed to fetch secrets:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSecrets();
  }, []);

  const handleUpdate = async () => {
    setIsSaving(true);
    try {
      // Only send keys that have a value
      const updates: Record<string, string> = {};
      Object.entries(formValues).forEach(([key, val]) => {
        if (val && val.trim() !== "") {
          updates[key] = val;
        }
      });

      if (Object.keys(updates).length > 0) {
        await api.updateSecrets(updates);
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
        fetchSecrets();
      }
    } catch (error) {
      console.error("Failed to update secrets:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleVisibility = (key: string) => {
    setVisibleKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="p-8 space-y-8 bg-background min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Secrets & Keys</h1>
          <p className="text-foreground/60 mt-1">Safely manage your API credentials and environment variables.</p>
        </div>
        <button 
          onClick={handleUpdate}
          disabled={isSaving}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all active:scale-95 disabled:opacity-50"
        >
          {isSaving ? <Activity className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
          {saveSuccess ? "Configuration Saved!" : "Save Changes"}
        </button>
      </div>

      <div className="max-w-4xl space-y-6">
        <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex gap-4 items-start">
          <ShieldAlert className="h-6 w-6 text-amber-500 shrink-0" />
          <div>
            <h3 className="text-sm font-bold text-amber-600 dark:text-amber-500 uppercase tracking-wider">Security Notice</h3>
            <p className="text-sm text-foreground/70 mt-1">API keys are stored in a centralized SQLite database. Masked values are returned by the API for existing keys. Entering a new value will overwrite the existing one.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {secretKeys.map((item) => (
            <div key={item.key} className="p-6 rounded-2xl bg-card border border-border flex flex-col md:flex-row md:items-center gap-6 group hover:bg-accent/5 transition-all shadow-sm">
              <div className="flex items-center gap-4 md:w-64 shrink-0">
                <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-500">
                  <Key className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-foreground leading-tight">{item.label}</h4>
                  <code className="text-[10px] text-foreground/40 uppercase tracking-tighter">{item.key}</code>
                </div>
              </div>

              <div className="flex-1 relative">
                <input 
                  type={visibleKeys[item.key] ? "text" : "password"} 
                  value={formValues[item.key] || ""}
                  onChange={e => setFormValues({...formValues, [item.key]: e.target.value})}
                  placeholder={
                    serverStatus[item.key]?.set 
                      ? (visibleKeys[item.key] ? serverStatus[item.key]?.value : "••••••••••••••••") 
                      : "Not configured"
                  }
                  className="w-full bg-accent/20 border border-border rounded-xl px-5 py-3 text-foreground focus:border-indigo-500/50 focus:ring-0 transition-all font-mono text-sm pr-12 placeholder:text-foreground/30"
                />
                <button 
                  type="button"
                  onClick={() => toggleVisibility(item.key)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-foreground/40 hover:text-foreground transition-colors"
                >
                  {visibleKeys[item.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              <div className="flex items-center gap-2 shrink-0 md:w-32 justify-end">
                {serverStatus[item.key]?.set && (
                  <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold uppercase">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Configured</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Activity(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}
