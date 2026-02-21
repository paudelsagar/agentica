"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <button
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className="relative h-10 w-10 flex items-center justify-center rounded-xl bg-accent/50 border border-border hover:bg-accent hover:border-indigo-500/30 transition-all duration-300 group shadow-sm active:scale-95"
      title="Toggle Theme"
      suppressHydrationWarning
    >
      <Sun className="h-[1.2rem] w-[1.2rem] transition-all duration-500 text-amber-500 dark:-rotate-90 dark:scale-0 dark:opacity-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 opacity-0 transition-all duration-500 text-indigo-400 dark:rotate-0 dark:scale-100 dark:opacity-100" />
      <span className="sr-only">Toggle theme</span>
    </button>
  )
}
