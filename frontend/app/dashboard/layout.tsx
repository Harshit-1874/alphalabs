"use client";

import { useEffect } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger, useSidebar } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { usePathname } from "next/navigation";
import { useUIStore } from "@/lib/stores";
import { GlobalDynamicIsland } from "@/components/ui/global-dynamic-island";
import type { AccentColor } from "@/types";

// Accent color mappings to HSL values
const accentColorMap: Record<AccentColor, { primary: string; ring: string }> = {
  cyan: { primary: "14 94% 48%", ring: "14 94% 48%" },      // Flame Orange (default brand)
  purple: { primary: "263 70% 60%", ring: "263 70% 60%" },  // Lavender Purple
  green: { primary: "142 71% 45%", ring: "142 71% 45%" },   // Green
  amber: { primary: "38 92% 50%", ring: "38 92% 50%" },     // Amber/Cream
};

// Map routes to page titles
const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/dashboard/agents": "My Agents",
  "/dashboard/agents/new": "Create New Agent",
  "/dashboard/arena/backtest": "Backtest Arena",
  "/dashboard/arena/forward": "Forward Test Arena",
  "/dashboard/results": "Results & Certificates",
  "/dashboard/settings": "Settings",
  "/dashboard/settings/api-keys": "API Keys",
  "/dashboard/settings/preferences": "Preferences",
};

// Keyboard shortcuts handler - must be inside SidebarProvider
function KeyboardShortcuts() {
  const { toggleSidebar } = useSidebar();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + B to toggle sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  return null;
}

// Apply accent color to CSS variables
function AccentColorProvider() {
  const { accentColor } = useUIStore();

  useEffect(() => {
    const colors = accentColorMap[accentColor];
    if (colors) {
      document.documentElement.style.setProperty("--primary", colors.primary);
      document.documentElement.style.setProperty("--ring", colors.ring);
      document.documentElement.style.setProperty("--sidebar-primary", colors.primary);
      document.documentElement.style.setProperty("--sidebar-ring", colors.ring);
    }
  }, [accentColor]);

  return null;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  
  // Get page title, defaulting to a capitalized version of the last path segment
  const getPageTitle = () => {
    if (pageTitles[pathname]) return pageTitles[pathname];
    
    // Check for dynamic routes
    if (pathname.startsWith("/dashboard/agents/") && pathname.includes("/edit")) {
      return "Edit Agent";
    }
    if (pathname.startsWith("/dashboard/agents/") && !pathname.includes("/new")) {
      return "Agent Details";
    }
    if (pathname.startsWith("/dashboard/arena/backtest/")) {
      return "Backtest Battle";
    }
    if (pathname.startsWith("/dashboard/arena/forward/")) {
      return "Live Session";
    }
    if (pathname.startsWith("/dashboard/results/")) {
      return "Test Result";
    }
    
    return "Dashboard";
  };

  return (
    <SidebarProvider>
      <KeyboardShortcuts />
      <AccentColorProvider />
      <GlobalDynamicIsland />
      <AppSidebar />
      <SidebarInset>
        {/* Top Header Bar */}
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <span className="font-mono text-sm font-medium text-muted-foreground">
              {getPageTitle()}
            </span>
          </div>
        </header>
        
        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          <div className="container max-w-[1400px] mx-auto px-3 py-4 sm:px-4 sm:py-6 md:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

