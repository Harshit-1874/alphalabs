"use client";

import { motion } from "motion/react";
import { Brain } from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";
import type { AnalyzingData } from "@/lib/stores/dynamic-island-store";
import { Waveform } from "../animated-components";

interface AnalyzingContentProps {
  data?: AnalyzingData;
  isExpanded?: boolean;
}

export const AnalyzingContent = ({ data, isExpanded }: AnalyzingContentProps) => {
  const message = data?.message || "Analyzing...";
  
  // Expanded view - show what AI is looking for
  if (isExpanded && data) {
    const phaseInfo = {
      scanning: { title: "Scanning Market", hint: "Looking for entry signals..." },
      analyzing: { title: "Pattern Analysis", hint: "Evaluating price action..." },
      deciding: { title: "Making Decision", hint: "Calculating risk/reward..." },
      executing: { title: "Executing", hint: "Placing order..." },
    };
    const info = phaseInfo[data.phase || "analyzing"] || phaseInfo.analyzing;
    
    return (
      <DynamicContainer className="flex h-full w-full items-center justify-between px-5">
        <motion.div 
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
        >
          <motion.div
            className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--brand-flame)/0.15)]"
            initial={{ scale: 0, rotate: -90 }}
            animate={{ scale: [1, 1.05, 1], rotate: 0 }}
            transition={{ 
              scale: { duration: 2, repeat: Infinity },
              rotate: { type: "spring", stiffness: 500, damping: 25 }
            }}
          >
            <Brain className="h-5 w-5 text-[hsl(var(--brand-flame))]" />
          </motion.div>
          <motion.div 
            className="flex flex-col"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <span className="text-sm font-semibold text-white">{info.title}</span>
            <span className="text-xs text-white/50">{info.hint}</span>
          </motion.div>
        </motion.div>
        <motion.div 
          className="flex items-center gap-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
        >
          <Waveform color="hsl(var(--brand-flame))" />
          {data.currentAsset && (
            <span className="text-xs font-mono text-white/60">{data.currentAsset}</span>
          )}
        </motion.div>
      </DynamicContainer>
    );
  }
  
  // Compact view - simplified to match idle "AI Ready" size
  const phaseInfo = {
    scanning: { 
      label: "Scanning", 
      color: "hsl(var(--accent-amber))",
    },
    analyzing: { 
      label: "Analyzing", 
      color: "hsl(var(--brand-flame))",
    },
    deciding: { 
      label: "Deciding", 
      color: "hsl(var(--accent-profit))",
    },
    executing: { 
      label: "Executing", 
      color: "hsl(var(--brand-flame))",
    },
  };
  const phase = phaseInfo[data?.phase || "analyzing"] || phaseInfo.analyzing;
  
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-center">
      <div className="flex items-center gap-2 px-4">
        {/* Left: Pulsing dot (similar to idle state) */}
        <div className="relative">
          <motion.div 
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: phase.color }}
            animate={{ 
              scale: [1, 1.2, 1],
              boxShadow: [
                `0 0 0px ${phase.color}`,
                `0 0 8px ${phase.color}`,
                `0 0 0px ${phase.color}`,
              ]
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        
        {/* Center: Phase text (similar to "AI Ready" format) */}
        <motion.span 
          className="text-xs font-medium text-white/70"
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          {phase.label}
        </motion.span>
        
        {/* Right: Small waveform indicator */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
          className="scale-75"
        >
          <Waveform color={phase.color} />
        </motion.div>
      </div>
    </DynamicContainer>
  );
};

