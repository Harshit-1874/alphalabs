"use client";

import { motion } from "motion/react";
import { Brain, Target, TrendingUp, BarChart3, Zap, Activity } from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";
import type { AnalyzingData } from "@/lib/stores/dynamic-island-store";
import { Waveform } from "../animated-components";

interface AnalyzingContentProps {
  data?: AnalyzingData;
  isExpanded?: boolean;
}

const PHASE_CONFIG = {
  scanning: { 
    title: "Scanning", 
    hint: "Looking for signals",
    icon: Target,
    color: "hsl(var(--accent-amber))",
    hexColor: "#f59e0b",
  },
  analyzing: { 
    title: "Analyzing", 
    hint: "Evaluating patterns",
    icon: BarChart3,
    color: "hsl(var(--brand-flame))",
    hexColor: "#E8400D",
  },
  deciding: { 
    title: "Deciding", 
    hint: "Calculating R/R",
    icon: TrendingUp,
    color: "hsl(var(--accent-profit))",
    hexColor: "#22c55e",
  },
  executing: { 
    title: "Executing", 
    hint: "Placing order",
    icon: Zap,
    color: "hsl(var(--brand-flame))",
    hexColor: "#E8400D",
  },
};

export const AnalyzingContent = ({ data, isExpanded }: AnalyzingContentProps) => {
  const message = data?.message || "Analyzing...";
  const phaseKey = data?.phase || "analyzing";
  const phase = PHASE_CONFIG[phaseKey] || PHASE_CONFIG.analyzing;
  const PhaseIcon = phase.icon;
  
  // Expanded view - rich dashboard layout
  if (isExpanded && data) {
    return (
      <DynamicContainer className="flex h-full w-full flex-col gap-2 px-4 pt-3 pb-3">
        {/* Header */}
        <motion.div 
          className="flex items-center justify-between pb-1.5 border-b border-white/10"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <div className="flex items-center gap-2">
            <div className="relative">
              <motion.div 
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: phase.hexColor }}
                animate={{ 
                  scale: [1, 1.3, 1],
                  boxShadow: [
                    `0 0 0px ${phase.hexColor}`,
                    `0 0 10px ${phase.hexColor}`,
                    `0 0 0px ${phase.hexColor}`,
                  ]
                }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
            
            <div className="flex items-center gap-1.5">
              <Brain className="h-3.5 w-3.5" style={{ color: phase.hexColor }} />
              <span className="text-xs font-bold text-white">
                AI Active
              </span>
              <motion.span 
                className="text-[10px] font-semibold uppercase"
                style={{ color: phase.hexColor }}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                {phase.title}
              </motion.span>
            </div>
          </div>
          
          {data.currentAsset && (
            <motion.div 
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-full border"
              style={{ 
                backgroundColor: `${phase.hexColor}15`,
                borderColor: `${phase.hexColor}30`,
              }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <Activity className="h-3 w-3" style={{ color: phase.hexColor }} />
              <span className="text-[10px] font-mono font-semibold" style={{ color: phase.hexColor }}>
                {data.currentAsset}
              </span>
            </motion.div>
          )}
        </motion.div>

        {/* Cards Row */}
        <motion.div 
          className="flex items-stretch gap-2"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          {/* Phase Card */}
          <motion.div
            className="flex-[2.5] rounded-xl px-2.5 py-2 border relative overflow-hidden"
            style={{ 
              backgroundColor: `${phase.hexColor}10`,
              borderColor: `${phase.hexColor}40`,
            }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <motion.div
              className="absolute inset-0"
              style={{ 
                background: `radial-gradient(circle at 80% 20%, ${phase.hexColor}20, transparent 60%)`,
              }}
              animate={{ opacity: [0.3, 0.5, 0.3] }}
              transition={{ duration: 3, repeat: Infinity }}
            />
            
            <div className="relative flex items-center justify-between">
              <div>
                <p className="text-[8px] font-semibold text-white/40 uppercase tracking-wide">
                  Phase
                </p>
                <motion.p 
                  className="text-sm font-bold text-white leading-tight"
                  key={phase.title}
                  initial={{ opacity: 0, y: 3 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {phase.title}
                </motion.p>
                <p className="text-[9px] font-medium mt-0.5" style={{ color: phase.hexColor }}>
                  {phase.hint}
                </p>
              </div>
              
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="p-1.5 rounded-lg"
                style={{ backgroundColor: `${phase.hexColor}15` }}
              >
                <PhaseIcon className="h-4 w-4" style={{ color: phase.hexColor }} />
              </motion.div>
            </div>
          </motion.div>

          {/* Status Card */}
          <motion.div
            className="flex-1 rounded-xl bg-white/5 border border-white/10 px-2.5 py-2 flex items-center justify-center"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
          >
            <div className="flex flex-col items-center gap-1">
              <Waveform color={phase.hexColor} />
              <p className="text-[8px] text-white/40 uppercase font-semibold">Status</p>
              <p className="text-[11px] font-bold text-white leading-tight">
                Active
              </p>
            </div>
          </motion.div>
        </motion.div>

        {/* Info Bar */}
        <motion.div
          className="flex-1 rounded-xl bg-white/5 border border-white/10 px-3 py-2 flex items-center"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="relative flex items-center gap-2.5 w-full">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            >
              <Brain className="h-3.5 w-3.5 shrink-0" style={{ color: phase.hexColor }} />
            </motion.div>
            
            <motion.p 
              className="text-[11px] text-white/85 leading-relaxed flex-1 min-w-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {message}
            </motion.p>
            
            <div className="flex items-center gap-0.5">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-1 w-1 rounded-full"
                  style={{ backgroundColor: phase.hexColor }}
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          </div>
        </motion.div>
      </DynamicContainer>
    );
  }
  
  // Compact view - keep original simple design
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-center">
      <div className="flex items-center gap-2 px-4">
        {/* Pulsing dot */}
        <div className="relative">
          <motion.div 
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: phase.hexColor }}
            animate={{ 
              scale: [1, 1.2, 1],
              boxShadow: [
                `0 0 0px ${phase.hexColor}`,
                `0 0 8px ${phase.hexColor}`,
                `0 0 0px ${phase.hexColor}`,
              ]
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        
        {/* Phase text */}
        <motion.span 
          className="text-xs font-medium text-white/70"
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          {phase.title}
        </motion.span>
        
        {/* Waveform */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
          className="scale-75"
        >
          <Waveform color={phase.hexColor} />
        </motion.div>
      </div>
    </DynamicContainer>
  );
};
