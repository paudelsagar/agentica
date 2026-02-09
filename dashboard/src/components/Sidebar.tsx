"use client";

import { clsx, type ClassValue } from "clsx";
import {
  BarChart3,
  Cpu,
  LayoutDashboard,
  MessageSquare,
  Settings,
  ShieldCheck,
  Users
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { twMerge } from "tailwind-merge";
import { ThemeToggle } from "./theme-toggle";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Chat", href: "/chat", icon: MessageSquare },
  { name: "Agents", href: "/agents", icon: Users },
  { name: "MCP Servers", href: "/mcp", icon: Cpu },
  { name: "Secrets", href: "/secrets", icon: ShieldCheck },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Metrics", href: "/metrics", icon: BarChart3 },
];


export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="flex h-20 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            A
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">Agentica</span>
        </div>
        <ThemeToggle />
      </div>

      <nav className="flex-1 space-y-1 px-4 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                isActive 
                  ? "bg-indigo-600/10 text-indigo-500 shadow-sm" 
                  : "text-foreground/60 hover:bg-accent hover:text-foreground"
              )}
            >
              <item.icon className={cn(
                "mr-3 h-5 w-5 transition-colors",
                isActive ? "text-indigo-500" : "text-foreground/40 group-hover:text-foreground"
              )} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="rounded-xl bg-accent/50 p-4">
          <p className="text-xs font-medium text-foreground/40 uppercase tracking-wider mb-2">Backend Status</p>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-medium text-foreground/80">Online</span>
          </div>
        </div>
      </div>
    </div>
  );
}
