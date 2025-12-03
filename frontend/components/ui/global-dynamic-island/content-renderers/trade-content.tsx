"use client";

import { motion } from "motion/react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { DynamicContainer, DynamicTitle, DynamicDescription } from "@/components/ui/dynamic-island";
import type { TradeData } from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";

interface TradeContentProps {
  data: TradeData;
  isExpanded?: boolean;
}

export const TradeContent = ({ data, isExpanded }: TradeContentProps) => {
  const isLong = data.direction === "long";
  
  // Expanded view - clean organized layout with better spacing
  if (isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full flex-col justify-center gap-3 px-5 py-3">
        {/* Top row: Icon + Main Info */}
        <motion.div 
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
        >
          <motion.div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
              isLong ? "bg-[hsl(var(--accent-profit)/0.2)]" : "bg-[hsl(var(--accent-red)/0.2)]"
            )}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 20, delay: 0.1 }}
          >
            {isLong ? (
              <TrendingUp className="h-5 w-5 text-[hsl(var(--accent-profit))]" />
            ) : (
              <TrendingDown className="h-5 w-5 text-[hsl(var(--accent-red))]" />
            )}
          </motion.div>
          <motion.div 
            className="flex-1 min-w-0"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold text-white">
                {isLong ? "LONG" : "SHORT"}
              </span>
              <span className="text-xs font-medium text-white/70">{data.asset}</span>
            </div>
            {data.reasoning && (
              <p className="text-[10px] text-white/50 line-clamp-1 mt-0.5">
                {data.reasoning}
              </p>
            )}
          </motion.div>
          {data.confidence && (
            <motion.div 
              className="flex items-center gap-1 rounded-full bg-white/10 px-2 py-1"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 500 }}
            >
              <span className="font-mono text-xs font-bold text-[hsl(var(--accent-profit))]">{data.confidence}%</span>
            </motion.div>
          )}
        </motion.div>
        
        {/* Bottom row: Key Levels in organized grid */}
        <motion.div 
          className="flex items-center gap-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5 flex-1">
            <div className="text-center">
              <p className="text-[9px] text-white/40 uppercase tracking-wide mb-0.5">Entry</p>
              <p className="font-mono text-xs font-semibold text-white">${(data.entryPrice/1000).toFixed(1)}k</p>
            </div>
          </div>
          {data.stopLoss && (
            <div className="flex items-center gap-2 rounded-lg bg-[hsl(var(--accent-red)/0.1)] px-3 py-1.5 flex-1">
              <div className="text-center">
                <p className="text-[9px] text-white/40 uppercase tracking-wide mb-0.5">Stop Loss</p>
                <p className="font-mono text-xs font-semibold text-[hsl(var(--accent-red))]">${(data.stopLoss/1000).toFixed(1)}k</p>
              </div>
            </div>
          )}
          {data.takeProfit && (
            <div className="flex items-center gap-2 rounded-lg bg-[hsl(var(--accent-profit)/0.1)] px-3 py-1.5 flex-1">
              <div className="text-center">
                <p className="text-[9px] text-white/40 uppercase tracking-wide mb-0.5">Take Profit</p>
                <p className="font-mono text-xs font-semibold text-[hsl(var(--accent-profit))]">${(data.takeProfit/1000).toFixed(1)}k</p>
              </div>
            </div>
          )}
        </motion.div>
      </DynamicContainer>
    );
  }
  
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <motion.div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full relative",
            isLong 
              ? "bg-[hsl(var(--accent-profit)/0.2)]" 
              : "bg-[hsl(var(--accent-red)/0.2)]"
          )}
          initial={{ scale: 0, rotate: -90 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 600, damping: 20, delay: 0.05 }}
        >
          <motion.div
            className={cn(
              "absolute inset-0 rounded-full",
              isLong ? "bg-[hsl(var(--accent-profit))]" : "bg-[hsl(var(--accent-red))]"
            )}
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 2.5, opacity: 0 }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
          <motion.div
            initial={{ y: isLong ? 5 : -5, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 20, delay: 0.15 }}
          >
            {isLong ? (
              <TrendingUp className="h-4 w-4 text-[hsl(var(--accent-profit))]" />
            ) : (
              <TrendingDown className="h-4 w-4 text-[hsl(var(--accent-red))]" />
            )}
          </motion.div>
        </motion.div>
        <div className="flex flex-col">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15, type: "spring", stiffness: 500 }}
          >
            <DynamicDescription className="text-xs text-white/60">
              {isLong ? "LONG" : "SHORT"} {data.asset}
            </DynamicDescription>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 500 }}
          >
            <DynamicTitle className="font-mono text-sm font-bold text-white">
              ${data.entryPrice.toLocaleString()}
            </DynamicTitle>
          </motion.div>
        </div>
      </div>
      {data.confidence && (
        <motion.div 
          className="flex items-center gap-1 rounded-full bg-white/10 px-2 py-1"
          initial={{ opacity: 0, scale: 0.5, x: 10 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ delay: 0.25, type: "spring", stiffness: 500 }}
        >
          <span className="text-[10px] font-medium text-white/70">
            {data.confidence}%
          </span>
        </motion.div>
      )}
    </DynamicContainer>
  );
};

