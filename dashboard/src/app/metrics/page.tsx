"use client";

import { api } from "@/lib/api";
import { cn, formatCompactNumber } from "@/lib/utils";
import { Activity, BarChart3, Clock, Filter, RefreshCw, X, Zap } from "lucide-react";
import { useTheme } from "next-themes";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"];

const TIME_RANGES = [
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "Last Week", value: "last_week" },
  { label: "Last Month", value: "last_month" },
  { label: "Last 3 Months", value: "last_3_months" },
  { label: "Last 6 Months", value: "last_6_months" },
  { label: "Last Year", value: "last_year" },
  { label: "All", value: "all" }
];

function getTimeRangeDates(range: string) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  // Helper to format date as ISO string (YYYY-MM-DDTHH:mm:ss)
  const toISO = (d: Date) => d.toISOString();

  switch (range) {
    case "today":
      return { startDate: toISO(today), endDate: toISO(new Date()) };
    case "yesterday": {
      const start = new Date(today);
      start.setDate(today.getDate() - 1);
      const end = new Date(today);
      return { startDate: toISO(start), endDate: toISO(end) };
    }
    case "last_week": {
      const start = new Date(today);
      start.setDate(today.getDate() - 7);
      return { startDate: toISO(start), endDate: toISO(new Date()) };
    }
    case "last_month": {
      const start = new Date(today);
      start.setMonth(today.getMonth() - 1);
      return { startDate: toISO(start), endDate: toISO(new Date()) };
    }
    case "last_3_months": {
      const start = new Date(today);
      start.setMonth(today.getMonth() - 3);
      return { startDate: toISO(start), endDate: toISO(new Date()) };
    }
    case "last_6_months": {
      const start = new Date(today);
      start.setMonth(today.getMonth() - 6);
      return { startDate: toISO(start), endDate: toISO(new Date()) };
    }
    case "last_year": {
      const start = new Date(today);
      start.setFullYear(today.getFullYear() - 1);
      return { startDate: toISO(start), endDate: toISO(new Date()) };
    }
    case "all":
    default:
      return { startDate: undefined, endDate: undefined };
  }
}

function MetricsDashboard() {
  const [metrics, setMetrics] = useState<any[]>([]);
  const [modelMetrics, setModelMetrics] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [timeRange, setTimeRange] = useState("day"); // For the trend chart interval
  const [selectedTimeRange, setSelectedTimeRange] = useState("last_month"); // For Global Filter
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const { theme } = useTheme();
  
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Initialize selectedTimeRange from URL or default
  useEffect(() => {
    const rangeParam = searchParams.get("range");
    if (rangeParam && TIME_RANGES.some(r => r.value === rangeParam)) {
      setSelectedTimeRange(rangeParam);
    } else if (!rangeParam) {
      setSelectedTimeRange("last_month");
    }
  }, [searchParams]);

  const handleTimeRangeChange = (newRange: string) => {
    setSelectedTimeRange(newRange);
    const params = new URLSearchParams(searchParams.toString());
    params.set("range", newRange);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const fetchMetrics = async () => {
    setIsLoading(true);
    try {
      const { startDate, endDate } = getTimeRangeDates(selectedTimeRange);

      const [metricsData, historyData, modelData] = await Promise.all([
        api.getMetrics(startDate, endDate),
        api.getMetricsHistory(timeRange, selectedAgent || undefined, selectedModel || undefined, startDate, endDate),
        api.getMetricsByModel(startDate, endDate)
      ]);

      const formattedMetrics = Object.entries(metricsData).map(([name, stats]: [string, any]) => ({
        name,
        ...stats
      }));
      setMetrics(formattedMetrics);
      setHistory(historyData || []);
      setModelMetrics(modelData || []);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const timer = setInterval(() => fetchMetrics(), 30000);
    return () => clearInterval(timer);
  }, [timeRange, selectedAgent, selectedModel, selectedTimeRange]);

  const chartAxisColor = theme === "light" ? "#64748b" : "#94a3b8";
  const chartGridColor = theme === "light" ? "#e2e8f0" : "#334155";
  const tooltipBg = theme === "light" ? "#ffffff" : "#0f172a";
  const tooltipBorder = theme === "light" ? "#e2e8f0" : "#1e293b";
  const tooltipText = theme === "light" ? "#0f172a" : "#ffffff";

  return (
    <div className="p-8 space-y-8 bg-background min-h-screen">
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">System Metrics</h1>
          <p className="text-foreground/60 mt-1">Real-time performance profiling and resource usage.</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="relative">
            <select
              value={selectedTimeRange}
              onChange={(e) => handleTimeRangeChange(e.target.value)}
              className="pl-3 pr-8 py-2 text-sm font-medium bg-background border border-border rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none cursor-pointer hover:bg-accent/50 transition-colors min-w-[160px]"
            >
              {TIME_RANGES.map((range) => (
                <option key={range.value} value={range.value}>
                  {range.label}
                </option>
              ))}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
              <Clock className="h-4 w-4" />
            </div>
          </div>

          <button 
            onClick={fetchMetrics}
            className="flex items-center gap-2 text-sm text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors whitespace-nowrap"
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stats Cards */}
        <div className="agent-card bg-card border border-border shadow-sm">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-500">
              <Activity className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground/40 uppercase tracking-widest">Total Agent Calls</h3>
          </div>
          <p className="text-4xl font-bold text-foreground">
            {formatCompactNumber(metrics.reduce((acc, curr) => acc + curr.call_count, 0))}
          </p>
        </div>

        <div className="agent-card bg-card border border-border shadow-sm">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
              <Zap className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground/40 uppercase tracking-widest">Total Tokens</h3>
          </div>
          <p className="text-4xl font-bold text-foreground">
            {formatCompactNumber(metrics.reduce((acc, curr) => acc + curr.total_tokens, 0))}
          </p>
        </div>

        <div className="agent-card bg-card border border-border shadow-sm">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-500">
              <Clock className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-foreground/40 uppercase tracking-widest">Avg Latency</h3>
          </div>
          <p className="text-4xl font-bold text-foreground">
            {metrics.length > 0 
              ? Math.round(metrics.reduce((acc, curr) => acc + curr.avg_latency_ms, 0) / metrics.length).toLocaleString() 
              : 0}ms
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latency Chart */}
        <div className="agent-card !p-0 overflow-hidden min-h-[400px] flex flex-col bg-card border border-border shadow-sm">
          <div className="p-6 border-b border-border bg-accent/20">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500" />
              Latency per Agent (ms)
            </h3>
          </div>
          <div className="flex-1 p-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} horizontal={false} />
                <XAxis 
                  type="number" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(val) => `${val}ms`}
                />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  width={100}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: "12px", color: tooltipText }}
                  itemStyle={{ color: tooltipText }}
                  formatter={(value: any) => [`${value}ms`, "Latency"]}
                />
                <Bar dataKey="avg_latency_ms" radius={[0, 4, 4, 0]}>
                  {metrics.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Token Usage by Agent Chart */}
        <div className="agent-card !p-0 overflow-hidden min-h-[400px] flex flex-col bg-card border border-border shadow-sm">
          <div className="p-6 border-b border-border bg-accent/20">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-indigo-500" />
              Token Usage by Agent
            </h3>
          </div>
          <div className="flex-1 p-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} horizontal={false} />
                <XAxis 
                  type="number" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={formatCompactNumber}
                />
                <YAxis dataKey="name" type="category" stroke={chartAxisColor} fontSize={12} tickLine={false} axisLine={false} width={100} />
                <Tooltip 
                  contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: "12px", color: tooltipText }}
                  itemStyle={{ color: tooltipText }}
                  formatter={(value: any) => [value?.toLocaleString(), "Tokens"]}
                />
                <Bar dataKey="total_tokens" radius={[0, 4, 4, 0]}>
                  {metrics.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         {/* Token Distribution by Model */}
         <div className="lg:col-span-1 agent-card !p-0 overflow-hidden min-h-[350px] flex flex-col bg-card border border-border shadow-sm">
          <div className="p-6 border-b border-border bg-accent/20">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Zap className="h-5 w-5 text-indigo-500" />
              Token Usage by Model
            </h3>
          </div>
          <div className="flex-1 p-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelMetrics} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} horizontal={false} />
                <XAxis 
                  type="number" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={formatCompactNumber}
                />
                <YAxis 
                  dataKey="model" 
                  type="category" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  width={100}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: "12px", color: tooltipText }}
                  itemStyle={{ color: tooltipText }}
                  formatter={(value: any) => [value?.toLocaleString(), "Tokens"]}
                />
                <Bar dataKey="tokens" radius={[0, 4, 4, 0]}>
                  {modelMetrics.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Historical Token Trend */}
        <div className="lg:col-span-2 agent-card !p-0 overflow-hidden min-h-[350px] flex flex-col bg-card border border-border shadow-sm">
          <div className="p-6 border-b border-border bg-accent/20 flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-500" />
                Token Consumption Trend
              </h3>
              <div className="flex items-center gap-2">
                 <div className="flex bg-muted p-1 rounded-lg border border-border">
                  {["minute", "hour", "day", "week", "month"].map((t) => (
                    <button
                      key={t}
                      onClick={() => setTimeRange(t)}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-xs font-bold uppercase transition-all",
                        timeRange === t
                          ? "bg-background text-foreground shadow-sm ring-1 ring-border"
                          : "text-muted-foreground hover:text-foreground hover:bg-background/50"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2 text-sm text-foreground/60">
                <Filter className="h-4 w-4" />
                <span className="font-medium">Filter by:</span>
              </div>
              
              <div className="relative">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="pl-3 pr-8 py-1.5 text-sm bg-background border border-border rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none cursor-pointer hover:bg-accent/50 transition-colors min-w-[140px]"
                >
                  <option value="">All Agents</option>
                  {metrics.map((m) => (
                    <option key={m.name} value={m.name}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="relative">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="pl-3 pr-8 py-1.5 text-sm bg-background border border-border rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none cursor-pointer hover:bg-accent/50 transition-colors min-w-[140px]"
                >
                  <option value="">All Models</option>
                  {modelMetrics.map((m) => (
                    <option key={m.model} value={m.model}>{m.model}</option>
                  ))}
                </select>
              </div>

              {(selectedAgent || selectedModel) && (
                <button
                  onClick={() => {
                    setSelectedAgent("");
                    setSelectedModel("");
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 text-xs font-medium hover:bg-red-500/20 transition-colors ml-auto"
                >
                  <X className="h-3.5 w-3.5" />
                  Clear Filters
                </button>
              )}
            </div>
          </div>
          <div className="flex-1 p-6">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} vertical={false} />
                <XAxis 
                  dataKey="timestamp" 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={(value) => {
                    if (timeRange === "minute" || timeRange === "hour") return value.split(" ")[1] || value;
                    return value;
                  }}
                />
                <YAxis 
                  stroke={chartAxisColor} 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  tickFormatter={formatCompactNumber}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: "12px", color: tooltipText }}
                  itemStyle={{ color: tooltipText }}
                  formatter={(value: any) => [value?.toLocaleString(), "Tokens"]}
                />
                <Area 
                  type="monotone" 
                  dataKey="tokens" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorTokens)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MetricsPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading metrics...</div>}>
      <MetricsDashboard />
    </Suspense>
  );
}
