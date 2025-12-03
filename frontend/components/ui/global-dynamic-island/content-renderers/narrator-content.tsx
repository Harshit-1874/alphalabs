"use client";

import { motion } from "motion/react";
import { Brain } from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";
import type { NarratorData } from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";

interface NarratorContentProps {
  data: NarratorData;
  isExpanded?: boolean;
}

export const NarratorContent = ({ data, isExpanded }: NarratorContentProps) => {
  const hasDetails = Boolean(data.details);
  const hasMetrics = (data.metrics?.length ?? 0) > 0;

  // Expanded view - Compact layout matching live session style
  if (isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full flex-col gap-2 px-4 py-3 pb-2.5">
        {/* Header Section - Compact with border separator */}
        <motion.div 
          className="flex items-center justify-between pb-1.5 border-b border-white/10"
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <div className="flex items-center gap-2">
            <motion.div
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                data.type === "action" && "bg-[hsl(var(--accent-profit)/0.15)]",
                data.type === "result" && "bg-[hsl(var(--brand-flame)/0.15)]",
                data.type === "info" && "bg-white/10"
              )}
              initial={{ scale: 0, rotate: -90 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 600, damping: 20 }}
            >
              <Brain 
                className={cn(
                  "h-3.5 w-3.5",
                  data.type === "action" && "text-[hsl(var(--accent-profit))]",
                  data.type === "result" && "text-[hsl(var(--brand-flame))]",
                  data.type === "info" && "text-white/80"
                )} 
              />
            </motion.div>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-white/50">
              LLM Collective
            </span>
          </div>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
              data.type === "action" && "bg-[hsl(var(--accent-profit)/0.2)] text-[hsl(var(--accent-profit))]",
              data.type === "result" && "bg-[hsl(var(--brand-flame)/0.15)] text-[hsl(var(--brand-flame))]",
              data.type === "info" && "bg-white/10 text-white/70"
            )}
          >
            {data.type ?? "info"}
          </span>
        </motion.div>
        
        {/* Main Content - Compact card */}
        <motion.div
          className="rounded-lg bg-white/5 backdrop-blur-sm px-3 py-2 border border-white/10 flex-1 min-h-0"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08, type: "spring", stiffness: 400, damping: 30 }}
        >
          <p className="text-[12px] font-medium text-white/95 leading-relaxed">
            {data.text}
          </p>
          {hasDetails && (
            <p className="text-[10px] text-white/60 mt-1.5 leading-relaxed">
              {data.details}
            </p>
          )}
        </motion.div>

        {/* Metrics Grid - Compact flex layout */}
        {hasMetrics && (
          <motion.div
            className="flex items-stretch gap-1.5"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, type: "spring", stiffness: 420, damping: 28 }}
          >
            {data.metrics?.map((metric, index) => (
              <motion.div
                key={`${metric.label}-${index}`}
                className="flex-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 min-w-0"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + index * 0.05, type: "spring", stiffness: 500, damping: 30 }}
              >
                <p className="text-[9px] uppercase tracking-wide text-white/50 truncate">
                  {metric.label}
                </p>
                <p className="text-base font-semibold text-white/95 leading-tight truncate">
                  {metric.value}
                </p>
              </motion.div>
            ))}
          </motion.div>
        )}
      </DynamicContainer>
    );
  }

  // Compact view - Clean single line with icon
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-center px-4">
      <div className="flex items-center gap-2.5 max-w-full">
        <motion.div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
            data.type === "action" && "bg-[hsl(var(--accent-profit)/0.15)]",
            data.type === "result" && "bg-[hsl(var(--brand-flame)/0.15)]",
            data.type === "info" && "bg-white/10"
          )}
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 600, damping: 25 }}
        >
          <Brain 
            className={cn(
              "h-3.5 w-3.5",
              data.type === "action" && "text-[hsl(var(--accent-profit))]",
              data.type === "result" && "text-[hsl(var(--brand-flame))]",
              data.type === "info" && "text-white/80"
            )} 
          />
        </motion.div>
        <motion.div
          className="flex-1 min-w-0"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 500, damping: 30 }}
        >
          <p className="text-sm font-medium text-white/95 truncate">
            {data.text}
          </p>
        </motion.div>
      </div>
    </DynamicContainer>
  );
};

