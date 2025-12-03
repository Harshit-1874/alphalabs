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
  // Expanded view - Beautiful card-like design for AI thoughts
  if (isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full flex-col gap-2 px-4 py-3">
        {/* Header with icon and label */}
        <motion.div 
          className="flex items-center gap-2"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
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
            AI Analysis
          </span>
        </motion.div>
        
        {/* Content card with beautiful styling */}
        <motion.div
          className="rounded-lg bg-white/5 backdrop-blur-sm px-3 py-2 border border-white/10"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 400, damping: 30 }}
        >
          <p className="text-[13px] font-medium text-white/95 leading-relaxed">
            {data.text}
          </p>
        </motion.div>
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

