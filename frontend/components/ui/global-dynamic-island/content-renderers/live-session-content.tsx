"use client";

import { motion, AnimatePresence } from "motion/react";
import { Clock, Activity, TrendingUp, TrendingDown, Zap, Target, BarChart3, Sparkles } from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";
import type { LiveSessionData } from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";

interface LiveSessionContentProps {
  data: LiveSessionData;
  isExpanded?: boolean;
}

export const LiveSessionContent = ({ data, isExpanded }: LiveSessionContentProps) => {
  const isProfitable = data.pnl >= 0;
  const pnlColor = isProfitable ? "hsl(var(--accent-profit))" : "hsl(var(--accent-red))";
  const TrendIcon = isProfitable ? TrendingUp : TrendingDown;
  
  // Expanded view - RICH DASHBOARD with ALL the data
  if (isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full flex-col gap-2 px-4 py-3 pb-2.5">
        {/* Header Section - More prominent with agent info */}
        <motion.div 
          className="flex items-center justify-between pb-1.5 border-b border-white/10"
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <div className="flex items-center gap-2">
            {/* Animated Status Indicator */}
            <div className="relative">
              <motion.div 
                className="h-2 w-2 rounded-full bg-[hsl(var(--accent-profit))]"
                animate={{ 
                  scale: [1, 1.4, 1],
                  boxShadow: [
                    "0 0 0px hsl(var(--accent-profit))",
                    "0 0 12px hsl(var(--accent-profit))",
                    "0 0 0px hsl(var(--accent-profit))",
                  ]
                }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <motion.div
                className="absolute inset-0 rounded-full bg-[hsl(var(--accent-profit))]"
                animate={{ 
                  scale: [1, 2.5], 
                  opacity: [0.7, 0] 
                }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
            
            {/* Agent Name with Icon */}
            <div className="flex items-center gap-1.5">
              <motion.div
                initial={{ rotate: 0 }}
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              >
                <Sparkles className="h-3.5 w-3.5 text-[hsl(var(--accent-profit))]" />
              </motion.div>
              <div>
                <span className="text-xs font-black text-white tracking-tight">
                  {data.agentName}
                </span>
                <motion.span 
                  className="ml-1.5 text-[9px] font-bold text-[hsl(var(--accent-profit))] uppercase tracking-wide"
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 3, repeat: Infinity }}
                >
                  {data.status === "running" ? "Live" : "Paused"}
                </motion.span>
              </div>
            </div>
          </div>
          
          {/* Duration with Clock Animation */}
          <motion.div 
            className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/5 border border-white/10"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
            >
              <Clock className="h-3 w-3 text-white/60" />
            </motion.div>
            <span className="text-[10px] font-semibold text-white/70">{data.duration}</span>
          </motion.div>
        </motion.div>

        {/* Main Stats Grid - Complete redesign */}
        <motion.div 
          className="flex items-stretch gap-2"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15, type: "spring", stiffness: 400, damping: 30 }}
        >
          {/* Left: P&L - HERO Card with enhanced visuals */}
          <motion.div
            className="flex-[3] rounded-lg px-3 py-2 border-2 relative overflow-hidden shadow-lg"
            style={{ 
              backgroundColor: `${pnlColor.replace(')', '/0.12)')}`,
              borderColor: `${pnlColor.replace(')', '/0.5)')}`,
            }}
            whileHover={{ scale: 1.03, borderColor: pnlColor }}
            transition={{ type: "spring", stiffness: 400 }}
          >
            {/* Animated Background Gradient */}
            <motion.div
              className="absolute inset-0"
              style={{ 
                background: `radial-gradient(circle at 70% 20%, ${pnlColor.replace(')', '/0.25)')}, transparent 70%)`,
              }}
              animate={{ 
                scale: [1, 1.2, 1],
                opacity: [0.3, 0.5, 0.3],
              }}
              transition={{ duration: 4, repeat: Infinity }}
            />
            
            {/* Floating Particles */}
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-1 h-1 rounded-full"
                style={{ backgroundColor: pnlColor }}
                initial={{ 
                  x: Math.random() * 100, 
                  y: Math.random() * 80,
                  opacity: 0.2
                }}
                animate={{ 
                  y: [-20, 80],
                  opacity: [0.2, 0.6, 0.2],
                }}
                transition={{ 
                  duration: 3 + i, 
                  repeat: Infinity,
                  delay: i * 0.5,
                }}
              />
            ))}
            
            <div className="relative flex items-start justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <BarChart3 className="h-3 w-3 text-white/50" />
                  <p className="text-[9px] font-bold text-white/50 uppercase tracking-wider">
                    Profit & Loss
                  </p>
                </div>
                
                {/* Animated PnL Value */}
                <motion.div className="flex items-baseline gap-1.5">
                  <motion.p 
                    className="font-mono text-2xl font-black leading-none"
                    style={{ color: pnlColor }}
                    key={data.pnl}
                    initial={{ scale: 1.2, opacity: 0, y: -10 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  >
                    {isProfitable ? "+" : ""}{data.pnl.toFixed(2)}%
                  </motion.p>
                  
                  <motion.div
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 300 }}
                  >
                    <TrendIcon 
                      className="h-4 w-4 mb-0.5" 
                      style={{ color: pnlColor }}
                      strokeWidth={3}
                    />
                  </motion.div>
                </motion.div>
                
                {/* Equity Display with Animation */}
                {data.equity && (
                  <motion.div
                    className="flex items-center gap-1 mt-0.5"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <div className="h-0.5 w-0.5 rounded-full bg-white/30" />
                    <p className="text-[10px] font-semibold text-white/60">
                      ${data.equity.toLocaleString()} equity
                    </p>
                  </motion.div>
                )}
              </div>
              
              {/* Floating Icon Animation */}
              <motion.div
                className="mt-1"
                animate={{ 
                  y: [0, -4, 0],
                  rotate: [0, 5, 0, -5, 0],
                }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                <motion.div
                  className="p-1.5 rounded-lg"
                  style={{ 
                    backgroundColor: `${pnlColor.replace(')', '/0.15)')}`,
                  }}
                  whileHover={{ scale: 1.1, rotate: 10 }}
                >
                  <Zap 
                    className="h-5 w-5" 
                    style={{ color: pnlColor }}
                    strokeWidth={2.5}
                  />
                </motion.div>
              </motion.div>
            </div>
          </motion.div>

          {/* Right: Stats Column with Enhanced Cards */}
          <div className="flex-[2] flex flex-col gap-1.5">
            {/* Positions/Trades Card */}
            {(data.openPositions !== undefined || data.totalTrades !== undefined) && (
              <motion.div
                className="rounded-lg bg-gradient-to-br from-white/8 to-white/3 px-2 py-1.5 border border-white/15 flex-1 relative overflow-hidden backdrop-blur-sm"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2, type: "spring", stiffness: 400 }}
                whileHover={{ scale: 1.05, borderColor: "rgba(255,255,255,0.3)" }}
              >
                {/* Shimmer Effect */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                  initial={{ x: "-100%" }}
                  animate={{ x: "200%" }}
                  transition={{ duration: 2, repeat: Infinity, repeatDelay: 1 }}
                />
                
                <div className="relative">
                  <div className="flex items-center gap-1 mb-0.5">
                    <Target className="h-2.5 w-2.5 text-white/50" />
                    <p className="text-[8px] text-white/50 uppercase font-bold tracking-wide">
                      {data.openPositions !== undefined ? "Open Positions" : "Total Trades"}
                    </p>
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    {data.openPositions !== undefined && (
                      <>
                        <motion.span 
                          className="font-mono text-xl font-black text-white"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 0.3, type: "spring", stiffness: 400 }}
                        >
                          {data.openPositions}
                        </motion.span>
                        {data.totalTrades !== undefined && (
                          <motion.span 
                            className="text-[9px] font-semibold text-white/40"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.4 }}
                          >
                            / {data.totalTrades} total
                          </motion.span>
                        )}
                      </>
                    )}
                    {!data.openPositions && data.totalTrades !== undefined && (
                      <motion.span 
                        className="font-mono text-xl font-black text-white"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3, type: "spring", stiffness: 400 }}
                      >
                        {data.totalTrades}
                      </motion.span>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
            
            {/* Win Rate Card with Progress Bar */}
            {data.winRate !== undefined && (
              <motion.div
                className="rounded-lg bg-gradient-to-br from-white/8 to-white/3 px-2 py-1.5 border border-white/15 flex-1 relative overflow-hidden backdrop-blur-sm"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25, type: "spring", stiffness: 400 }}
                whileHover={{ scale: 1.05, borderColor: "rgba(255,255,255,0.3)" }}
              >
                {/* Shimmer Effect */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                  initial={{ x: "-100%" }}
                  animate={{ x: "200%" }}
                  transition={{ duration: 2, repeat: Infinity, repeatDelay: 1, delay: 0.5 }}
                />
                
                <div className="relative">
                  <div className="flex items-center gap-1 mb-0.5">
                    <Activity className="h-2.5 w-2.5 text-[hsl(var(--accent-profit))]" />
                    <p className="text-[8px] text-white/50 uppercase font-bold tracking-wide">
                      Win Rate
                    </p>
                  </div>
                  
                  <div className="space-y-1">
                    <motion.span 
                      className="font-mono text-xl font-black text-[hsl(var(--accent-profit))]"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.35, type: "spring", stiffness: 400 }}
                    >
                      {data.winRate}%
                    </motion.span>
                    
                    {/* Animated Progress Bar */}
                    <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-[hsl(var(--accent-profit))] to-green-400 rounded-full"
                        initial={{ width: "0%" }}
                        animate={{ width: `${data.winRate}%` }}
                        transition={{ delay: 0.5, duration: 1, ease: "easeOut" }}
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Bottom Activity Bar - Enhanced */}
        <motion.div
          className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 mb-0.5"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {data.nextDecisionIn ? (
            <>
              <div className="flex items-center gap-1.5">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Clock className="h-3 w-3 text-[hsl(var(--accent-profit))]" />
                </motion.div>
                <span className="text-[9px] font-semibold text-white/60">
                  Next decision in <span className="text-white font-bold">{data.nextDecisionIn}</span>
                </span>
              </div>
              
              {/* Animated Bars */}
              <motion.div
                className="flex items-center gap-0.5"
              >
                {[...Array(5)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-0.5 rounded-full bg-[hsl(var(--accent-profit))]"
                    animate={{ 
                      height: [4, 10, 4],
                      opacity: [0.4, 1, 0.4],
                    }}
                    transition={{ 
                      duration: 1.2, 
                      repeat: Infinity, 
                      delay: i * 0.15,
                      ease: "easeInOut",
                    }}
                  />
                ))}
              </motion.div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-1.5">
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Activity className="h-3 w-3 text-[hsl(var(--accent-profit))]" />
                </motion.div>
                <span className="text-[9px] font-semibold text-white/60">
                  Monitoring markets
                </span>
              </div>
              
              {/* Waveform Animation */}
              <motion.div className="flex items-center gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-0.5 rounded-full bg-[hsl(var(--accent-profit))]"
                    animate={{ 
                      height: [4, 10, 4],
                      opacity: [0.4, 1, 0.4],
                    }}
                    transition={{ 
                      duration: 1.2, 
                      repeat: Infinity, 
                      delay: i * 0.15,
                      ease: "easeInOut",
                    }}
                  />
                ))}
              </motion.div>
            </>
          )}
        </motion.div>
      </DynamicContainer>
    );
  }
  
  // Compact view - Enhanced with better animations
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-center">
      <div className="flex items-center gap-3 px-4">
        {/* Left: Enhanced Pulsing dot + LIVE */}
        <motion.div 
          className="flex items-center gap-1.5"
          initial={{ opacity: 0, x: -15 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 25 }}
        >
          <div className="relative">
            <motion.div 
              className="h-2 w-2 rounded-full bg-[hsl(var(--accent-profit))]"
              animate={{ 
                scale: [1, 1.4, 1],
                boxShadow: [
                  "0 0 0px hsl(var(--accent-profit))",
                  "0 0 10px hsl(var(--accent-profit))",
                  "0 0 0px hsl(var(--accent-profit))",
                ]
              }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <motion.div
              className="absolute inset-0 rounded-full bg-[hsl(var(--accent-profit))]"
              animate={{ scale: [1, 2.5], opacity: [0.7, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          <motion.span 
            className="text-[10px] font-black text-[hsl(var(--accent-profit))] uppercase tracking-wide"
            animate={{ opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Live
          </motion.span>
        </motion.div>
        
        {/* Center: Agent name with icon */}
        <motion.div 
          className="flex items-center gap-1.5"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, type: "spring", stiffness: 500, damping: 25 }}
        >
          <Sparkles className="h-3.5 w-3.5 text-white/70" />
          <span className="text-sm font-black text-white tracking-tight">
            {data.agentName}
          </span>
        </motion.div>
        
        {/* Right: Enhanced PnL badge */}
        <motion.div
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 border-2 shadow-lg relative overflow-hidden"
          style={{ 
            backgroundColor: `${pnlColor.replace(')', '/0.2)')}`,
            borderColor: `${pnlColor.replace(')', '/0.6)')}`,
          }}
          key={data.pnl}
          initial={{ opacity: 0, x: 15, scale: 0.8 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 500, damping: 25 }}
          whileHover={{ scale: 1.05 }}
        >
          {/* Background glow */}
          <motion.div
            className="absolute inset-0"
            style={{ 
              background: `radial-gradient(circle at center, ${pnlColor.replace(')', '/0.3)')}, transparent 70%)`,
            }}
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          
          <motion.div
            className="relative"
            animate={{ rotate: [0, 10, 0, -10, 0] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <TrendIcon className="h-3.5 w-3.5" style={{ color: pnlColor }} strokeWidth={2.5} />
          </motion.div>
          <span 
            className="relative font-mono text-sm font-black"
            style={{ color: pnlColor }}
          >
            {isProfitable ? "+" : ""}{data.pnl.toFixed(1)}%
          </span>
        </motion.div>
      </div>
    </DynamicContainer>
  );
};

