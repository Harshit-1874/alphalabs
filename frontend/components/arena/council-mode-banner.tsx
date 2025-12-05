"use client";

import { useState } from "react";
import { Brain, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CouncilModeBannerProps {
  onEnableCouncilMode?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function CouncilModeBanner({
  onEnableCouncilMode,
  onDismiss,
  className,
}: CouncilModeBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  const handleEnable = () => {
    onEnableCouncilMode?.();
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg border border-purple-500/20 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-purple-500/10 p-4",
        "shadow-lg shadow-purple-500/10 animate-in fade-in slide-in-from-top-2 duration-500",
        className
      )}
    >
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer" />
      
      <div className="relative flex items-start gap-4">
        {/* Icon */}
        <div className="flex-shrink-0">
          <div className="relative">
            <Brain className="h-10 w-10 text-purple-400 animate-pulse" />
            <Sparkles className="absolute -right-1 -top-1 h-4 w-4 text-yellow-400 animate-pulse" />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-lg bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              🧠 Introducing Council Mode
            </h3>
            <span className="rounded-full bg-purple-500/20 px-2 py-0.5 text-xs font-medium text-purple-400 border border-purple-500/30">
              EXPERIMENTAL
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Let multiple AI models <span className="font-medium text-foreground">debate, criticize, and collaborate</span> to reach 
            the best trading decision. More robust analysis through collective intelligence.
          </p>
          <div className="flex items-center gap-2 pt-1">
            {onEnableCouncilMode && (
              <Button
                size="sm"
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-md"
                onClick={handleEnable}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Try Council Mode
              </Button>
            )}
            <span className="text-xs text-muted-foreground">
              ⚡ Takes 3-5x longer but worth it
            </span>
          </div>
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 rounded-md p-1 hover:bg-white/10 transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>
    </div>
  );
}

