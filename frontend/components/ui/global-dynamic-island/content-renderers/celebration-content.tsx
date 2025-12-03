"use client";

import { motion } from "motion/react";
import { Trophy, BarChart3, Target, Sparkles } from "lucide-react";
import { DynamicContainer, DynamicTitle, DynamicDescription } from "@/components/ui/dynamic-island";
import type { CelebrationData } from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";

interface CelebrationContentProps {
  data: CelebrationData;
}

export const CelebrationContent = ({ data }: CelebrationContentProps) => {
  const isProfitable = data.pnl >= 0;
  
  return (
    <DynamicContainer className="flex h-full w-full flex-col items-center justify-center px-6 py-4">
      <div className="text-center">
        {/* Animated Trophy Icon */}
        <motion.div 
          className="flex justify-center mb-2"
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
        >
          <motion.div
            animate={isProfitable ? { 
              rotate: [0, -10, 10, -10, 10, 0],
              y: [0, -4, 0],
            } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Trophy 
              className={cn(
                "h-8 w-8",
                isProfitable ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
              )} 
            />
          </motion.div>
        </motion.div>
        
        {/* Animated PnL */}
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15, type: "spring", stiffness: 500 }}
        >
          <DynamicTitle 
            className={cn(
              "font-mono text-3xl font-black tracking-tight",
              isProfitable ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
            )}
          >
            {isProfitable ? "+" : ""}{data.pnl.toFixed(1)}%
          </DynamicTitle>
        </motion.div>
        
        {/* Stats with staggered animation */}
        <motion.div 
          className="flex items-center justify-center gap-4 mt-2"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          {data.trades !== undefined && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="flex items-center gap-1"
            >
              <BarChart3 className="h-3 w-3 text-white/40" />
              <DynamicDescription className="text-xs text-white/60">
                {data.trades} trades
              </DynamicDescription>
            </motion.div>
          )}
          {data.winRate !== undefined && (
            <motion.div
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.35 }}
              className="flex items-center gap-1"
            >
              <Target className="h-3 w-3 text-white/40" />
              <DynamicDescription className="text-xs text-white/60">
                {data.winRate}% win rate
              </DynamicDescription>
            </motion.div>
          )}
        </motion.div>
        
        {/* Message with sparkle */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex items-center justify-center gap-1 mt-2"
        >
          {isProfitable && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles className="h-3 w-3 text-[hsl(var(--accent-profit))]" />
            </motion.div>
          )}
          <DynamicDescription className="text-sm font-medium text-white/80">
            {isProfitable ? "Certificate Ready!" : "Better luck next time"}
          </DynamicDescription>
        </motion.div>
      </div>
    </DynamicContainer>
  );
};

