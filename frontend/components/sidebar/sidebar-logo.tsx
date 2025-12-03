"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

interface SidebarLogoProps {
  isCollapsed: boolean;
}

export function SidebarLogo({ isCollapsed }: SidebarLogoProps) {
  return (
    <Link
      href="/dashboard"
      className={cn(
        "flex items-center gap-3 px-2 py-4 transition-all duration-200",
        isCollapsed && "justify-center px-0"
      )}
    >
      {/* Logo Icon - Diamond shape */}
      <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
        <div className="absolute inset-0 rotate-45 rounded-sm bg-gradient-to-br from-[hsl(var(--brand-flame))] to-[hsl(var(--brand-lavender))] opacity-20" />
        <div className="absolute inset-1 rotate-45 rounded-sm bg-gradient-to-br from-[hsl(var(--brand-flame))] to-[hsl(var(--brand-lavender))]" />
        <span className="relative z-10 font-mono text-xs font-bold text-white">
          α
        </span>
      </div>

      {/* Logo Text */}
      {!isCollapsed && (
        <div className="flex flex-col">
          <span className="font-mono text-base font-bold tracking-tight text-foreground">
            ALPHALAB
          </span>
          <span className="text-[10px] tracking-wider text-muted-foreground">
            The Arena for AI Traders
          </span>
        </div>
      )}
    </Link>
  );
}

