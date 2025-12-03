"use client";

import { motion } from "motion/react";
import { Zap, TrendingUp, TrendingDown } from "lucide-react";
import { DynamicContainer, DynamicTitle, DynamicDescription } from "@/components/ui/dynamic-island";
import type { AlphaData } from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";

interface AlphaContentProps {
  data: AlphaData;
}

export const AlphaContent = ({ data }: AlphaContentProps) => {
  const isLong = data.direction === "long";
  
  return (
    <DynamicContainer className="flex h-full w-full flex-col justify-center px-6 py-4">
      <div className="flex flex-col gap-3">
        {/* Header with animated zap */}
        <motion.div 
          className="flex items-center gap-2"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
        >
          <motion.div
            animate={{ 
              scale: [1, 1.2, 1],
              rotate: [0, 5, -5, 0],
            }}
            transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 1 }}
          >
            <Zap className="h-5 w-5 text-[hsl(var(--brand-flame))]" />
          </motion.div>
          <DynamicTitle className="text-lg font-black tracking-tight text-white">
            ALPHA DETECTED
          </DynamicTitle>
          <motion.div
            className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--brand-flame))]"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        </motion.div>
        
        {/* Details */}
        <div className="flex items-center justify-between">
          <motion.div 
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1, type: "spring", stiffness: 400 }}
          >
            <motion.div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg relative",
                isLong 
                  ? "bg-[hsl(var(--accent-profit)/0.2)]" 
                  : "bg-[hsl(var(--accent-red)/0.2)]"
              )}
              initial={{ scale: 0, rotate: -90 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.15, type: "spring", stiffness: 500 }}
            >
              {isLong ? (
                <TrendingUp className="h-5 w-5 text-[hsl(var(--accent-profit))]" />
              ) : (
                <TrendingDown className="h-5 w-5 text-[hsl(var(--accent-red))]" />
              )}
            </motion.div>
            <div>
              <DynamicDescription className="text-sm font-bold text-white" delay={0.15}>
                {isLong ? "LONG" : "SHORT"} {data.asset}
              </DynamicDescription>
              {data.reason && (
                <DynamicDescription className="text-xs text-white/60 max-w-[200px] line-clamp-1" delay={0.2}>
                  {data.reason}
                </DynamicDescription>
              )}
            </div>
          </motion.div>
          
          {/* Confidence with count-up effect */}
          <motion.div 
            className="flex flex-col items-center"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 400 }}
          >
            <motion.span 
              className="font-mono text-2xl font-black text-[hsl(var(--accent-profit))]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {data.confidence}%
            </motion.span>
            <span className="text-[10px] text-white/50">CONFIDENCE</span>
          </motion.div>
        </div>
      </div>
    </DynamicContainer>
  );
};

