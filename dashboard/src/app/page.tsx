"use client";

import { api } from "@/lib/api";
import { cn, formatCompactNumber } from "@/lib/utils";
import {
  Activity,
  ArrowUpRight,
  Cpu,
  History,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Users,
  Zap
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState<any>({
    agents: 0,
    mcpServers: 0,
    totalTokens: 0,
    avgLatency: 0
  });
  const [recentTrajectories, setRecentTrajectories] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agents, mcp, metrics, trajectories] = await Promise.all([
          api.getAgents(),
          api.getMCPServers(),
          api.getMetrics(),
          api.getRecentTrajectories()
        ]);

        const metricValues = Object.values(metrics);
        setStats({
          agents: Object.keys(agents).length,
          mcpServers: Object.keys(mcp).length,
          totalTokens: metricValues.reduce((acc: number, curr: any) => acc + curr.total_tokens, 0),
          avgLatency: metricValues.length > 0 
            ? Math.round(metricValues.reduce((acc: number, curr: any) => acc + curr.avg_latency_ms, 0) / metricValues.length) 
            : 0
        });
        setRecentTrajectories(trajectories);
      } catch (e) {
        console.error("Dashboard overview error:", e);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="p-8 space-y-12 bg-background min-h-screen">
      {/* Welcome Header */}
      <div className="relative group max-w-5xl">
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200" />
        <div className="relative p-8 rounded-2xl bg-card border border-border shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <h1 className="text-4xl font-bold text-foreground tracking-tight">System Overview</h1>
              <p className="text-foreground/60 mt-2 text-lg">Orchestrating {stats.agents} specialized agents across {stats.mcpServers} tool infrastructures.</p>
            </div>
            <Link 
              href="/chat"
              className="flex items-center gap-2 px-8 py-4 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-500 shadow-xl shadow-indigo-500/20 transition-all active:scale-95 text-lg"
            >
              Start New Workflow
              <Zap className="h-5 w-5 fill-current" />
            </Link>
          </div>
        </div>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          label="Active Agents" 
          value={stats.agents} 
          icon={Users} 
          trend="+2 recent"
          color="indigo"
          href="/agents"
        />
        <StatCard 
          label="MCP Proxies" 
          value={stats.mcpServers} 
          icon={Cpu} 
          trend="Healthy"
          color="emerald"
          href="/mcp"
        />
        <StatCard 
          label="Avg Latency" 
          value={`${stats.avgLatency}ms`} 
          icon={TrendingUp} 
          trend="Stable"
          color="amber"
          href="/metrics"
        />
        <StatCard 
          label="Token Burn" 
          value={formatCompactNumber(stats.totalTokens)} 
          icon={Activity} 
          trend="Within Budget"
          color="blue"
          href="/metrics"
        />
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Actions */}
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-xl font-bold text-foreground flex items-center gap-3">
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 gap-4">
            <ActionCard 
              label="Add Knowledge Proxy" 
              desc="Connect new MCP tools"
              icon={Cpu}
              href="/mcp"
            />
            <ActionCard 
              label="Update Model Tiers" 
              desc="Reassign LLM backends"
              icon={Zap}
              href="/settings"
            />
            <ActionCard 
              label="Rotate API Keys" 
              desc="Security & secret rotation"
              icon={ShieldCheck}
              href="/secrets"
            />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground flex items-center gap-3">
              <History className="h-5 w-5 text-indigo-500" />
              Recent Trajectories
            </h2>
            <Link href="/chat" className="text-sm text-indigo-500 font-medium hover:underline">View All</Link>
          </div>
          
          <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
             {recentTrajectories.length === 0 ? (
               <div className="p-8 text-center space-y-4">
                  <div className="h-12 w-12 rounded-full bg-accent text-foreground/40 flex items-center justify-center mx-auto">
                     <MessageSquare className="h-6 w-6" />
                  </div>
                  <div>
                     <p className="text-foreground font-medium">No recent conversations found</p>
                     <p className="text-sm text-foreground/40 mt-1">Trajectories appear here once you start using the agents.</p>
                  </div>
                  <button className="px-6 py-2 rounded-lg bg-accent text-foreground/80 text-sm hover:bg-accent/80 transition-colors">
                    Refresh Now
                  </button>
               </div>
             ) : (
               <div className="divide-y divide-border">
                 {recentTrajectories.map((item, i) => (
                   <div key={i} className="p-4 flex items-center justify-between hover:bg-accent/5 transition-colors">
                     <div className="flex items-center gap-4">
                       <div className={cn(
                         "h-10 w-10 rounded-lg flex items-center justify-center",
                         item.success ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                       )}>
                         {item.success ? <ShieldCheck className="h-5 w-5" /> : <Activity className="h-5 w-5" />}
                       </div>
                       <div>
                         <h4 className="text-sm font-bold text-foreground">{item.agent}</h4>
                         <p className="text-xs text-foreground/60 max-w-[300px] truncate">{item.preview || "No preview available"}</p>
                       </div>
                     </div>
                     <div className="text-right">
                       <p className="text-xs font-mono text-foreground/40">{new Date(item.timestamp).toLocaleDateString()}</p>
                       <p className="text-xs font-mono text-foreground/40">{new Date(item.timestamp).toLocaleTimeString()}</p>
                     </div>
                   </div>
                 ))}
               </div>
             )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, trend, color, href }: any) {
  const colorMap: any = {
    indigo: "text-indigo-500 bg-indigo-500/10",
    emerald: "text-emerald-500 bg-emerald-500/10",
    amber: "text-amber-500 bg-amber-500/10",
    blue: "text-blue-500 bg-blue-500/10"
  };

  return (
    <Link href={href} className="agent-card group cursor-pointer border border-border bg-card shadow-sm hover:bg-accent/5">
      <div className="flex items-center justify-between mb-4">
        <div className={cn("p-2.5 rounded-xl border border-border/50", colorMap[color])}>
          <Icon className="h-5 w-5" />
        </div>
        <ArrowUpRight className="h-4 w-4 text-foreground/20 group-hover:text-foreground transition-colors" />
      </div>
      <p className="text-sm font-bold text-foreground/60 uppercase tracking-widest">{label}</p>
      <h3 className="text-3xl font-bold text-foreground mt-1">{value}</h3>
      <div className="mt-4 flex items-center gap-2">
        <span className={cn("text-xs font-bold uppercase", colorMap[color].split(" ")[0])}>{trend}</span>
      </div>
    </Link>
  );
}

function ActionCard({ label, desc, icon: Icon, href }: any) {
  return (
    <Link href={href} className="flex items-center gap-4 p-4 rounded-xl border border-border bg-card shadow-sm hover:bg-accent/5 transition-all group">
      <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-500 group-hover:bg-indigo-600 group-hover:text-white transition-all">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h4 className="text-foreground font-bold text-sm">{label}</h4>
        <p className="text-xs text-foreground/60">{desc}</p>
      </div>
    </Link>
  );
}
