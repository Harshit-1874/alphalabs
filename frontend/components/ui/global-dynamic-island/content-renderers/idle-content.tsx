"use client";

import { motion, AnimatePresence } from "motion/react";
import { DynamicContainer, DynamicTitle, DynamicDescription } from "@/components/ui/dynamic-island";
import { useEffect, useState } from "react";
import { TrendingUp, Brain, Zap } from "lucide-react";

// Cool formulas and algo descriptions to cycle through
const ALGO_STATES = [
  { 
    text: "∇f(x) = 0", 
    subtext: "gradient descent active",
    color: "hsl(var(--brand-flame))",
    icon: Brain
  },
  { 
    text: "σ² = E[(X-μ)²]", 
    subtext: "volatility analysis",
    color: "#22c55e",
    icon: TrendingUp
  },
  { 
    text: "RL: Q(s,a) ← max", 
    subtext: "reinforcement learning",
    color: "#3b82f6",
    icon: Zap
  },
  { 
    text: "∑ωᵢrᵢ → α", 
    subtext: "portfolio optimization",
    color: "#a855f7",
    icon: TrendingUp
  },
  { 
    text: "P(A|B) = P(B|A)P(A)/P(B)", 
    subtext: "bayesian inference",
    color: "#f59e0b",
    icon: Brain
  },
];

interface IdleContentProps {
  totalAgents?: number;
  averageProfit?: number;
  isExpanded?: boolean;
}

export const IdleContent = ({ 
  totalAgents = 0, 
  averageProfit = 0,
  isExpanded = false 
}: IdleContentProps) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showStats, setShowStats] = useState(false);
  const currentAlgo = ALGO_STATES[currentIndex];
  const Icon = currentAlgo.icon;

  // Cycle through algos, then eventually show stats
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = prev + 1;
        // After cycling through all algos twice, show stats if we have data
        if (next >= ALGO_STATES.length * 2 && (totalAgents > 0 || averageProfit !== 0)) {
          setShowStats(true);
          return prev;
        }
        return next % ALGO_STATES.length;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [totalAgents, averageProfit]);

  // Reset to algos after showing stats for a while
  useEffect(() => {
    if (showStats) {
      const timeout = setTimeout(() => {
        setShowStats(false);
        setCurrentIndex(0);
      }, 5000);
      return () => clearTimeout(timeout);
    }
  }, [showStats]);

  // Collapsed view - minimal, slick
  if (!isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full items-center justify-center">
        <AnimatePresence mode="wait">
          {!showStats ? (
            <motion.div 
              key="algo"
              className="relative flex items-center gap-2 px-2"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
            >
              {/* Animated icon */}
              <motion.div 
                className="relative"
                animate={{ 
                  rotate: [0, 5, -5, 0],
                }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: currentAlgo.color }} />
                <motion.div 
                  className="absolute inset-0 rounded-full blur-md"
                  style={{ backgroundColor: currentAlgo.color }}
                  animate={{ 
                    opacity: [0.3, 0.6, 0.3],
                  }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                />
              </motion.div>
              
              {/* Formula */}
              <motion.span 
                key={currentIndex}
                className="text-xs font-semibold tracking-tight"
                style={{ color: currentAlgo.color }}
                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                transition={{ duration: 0.4 }}
              >
                {currentAlgo.text}
              </motion.span>

              {/* Pulsing particles */}
              <motion.div 
                className="h-1 w-1 rounded-full"
                style={{ backgroundColor: currentAlgo.color }}
                animate={{ 
                  scale: [0, 1.5, 0],
                  opacity: [0, 1, 0],
                }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              />
            </motion.div>
          ) : (
            <motion.div 
              key="stats"
              className="flex items-center gap-3 px-3"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
            >
              {totalAgents > 0 && (
                <motion.div 
                  className="flex items-center gap-1.5"
                  initial={{ x: -10, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] font-bold text-cyan-400">{totalAgents}</span>
                    <span className="text-[8px] text-white/40">agents</span>
                  </div>
                </motion.div>
              )}
              
              <motion.div 
                className="h-3 w-[1px] bg-white/20"
                initial={{ scaleY: 0 }}
                animate={{ scaleY: 1 }}
                transition={{ delay: 0.2 }}
              />
              
              {averageProfit !== 0 && (
                <motion.div 
                  className="flex items-center gap-1.5"
                  initial={{ x: 10, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="flex flex-col items-center">
                    <span className={`text-[10px] font-bold ${averageProfit > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {averageProfit > 0 ? '+' : ''}{averageProfit.toFixed(1)}%
                    </span>
                    <span className="text-[8px] text-white/40">avg profit</span>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </DynamicContainer>
    );
  }

  // Expanded view - more details and animations
  return (
    <DynamicContainer className="flex h-full w-full flex-col items-center justify-center gap-3 p-4">
      <AnimatePresence mode="wait">
        {!showStats ? (
          <motion.div 
            key="algo-expanded"
            className="flex flex-col items-center gap-3 w-full"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
          >
            {/* Large animated icon */}
            <motion.div 
              className="relative mb-2"
              animate={{ 
                rotate: [0, 5, -5, 0],
                scale: [1, 1.1, 1],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            >
              <Icon className="h-9 w-9 sm:h-10 sm:w-10" style={{ color: currentAlgo.color }} />
              <motion.div 
                className="absolute inset-0 rounded-full blur-xl"
                style={{ backgroundColor: currentAlgo.color }}
                animate={{ 
                  opacity: [0.3, 0.7, 0.3],
                  scale: [1, 1.5, 1],
                }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              />
            </motion.div>
            
            {/* Formula with glow */}
            <DynamicTitle className="text-3xl font-black tracking-tight text-center leading-tight sm:text-4xl">
              <motion.span
                key={currentIndex}
                className="inline-flex max-w-[90%] text-balance justify-center"
                style={{ color: currentAlgo.color }}
                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                transition={{ duration: 0.4 }}
              >
                {currentAlgo.text}
              </motion.span>
            </DynamicTitle>
            
            {/* Subtext */}
            <DynamicDescription className="text-xs text-white/60 font-medium">
              <motion.span
                key={`sub-${currentIndex}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
              >
                {currentAlgo.subtext}
              </motion.span>
            </DynamicDescription>

            {/* Particle effects */}
            <div className="relative w-full h-8 flex items-center justify-center">
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute h-1 w-1 rounded-full"
                  style={{ backgroundColor: currentAlgo.color }}
                  animate={{
                    x: [0, (i - 2) * 20, 0],
                    y: [0, -10, 0],
                    opacity: [0, 1, 0],
                    scale: [0, 1.5, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.2,
                    ease: "easeInOut",
                  }}
                />
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div 
            key="stats-expanded"
            className="flex flex-col items-center gap-3 w-full"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
          >
            <DynamicTitle className="text-lg font-bold text-white/90 mb-2">
              Your Trading Empire
            </DynamicTitle>
            
            <div className="flex items-center justify-around w-full px-4">
              {totalAgents > 0 && (
                <motion.div 
                  className="flex flex-col items-center gap-1"
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", delay: 0.1 }}
                >
                  <motion.div 
                    className="text-3xl font-black text-cyan-400"
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    {totalAgents}
                  </motion.div>
                  <span className="text-xs text-white/50">Agents Created</span>
                  <motion.div 
                    className="h-1 w-12 rounded-full bg-cyan-400/30"
                    animate={{ scaleX: [0, 1, 0], opacity: [0, 1, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                </motion.div>
              )}
              
              {averageProfit !== 0 && (
                <motion.div 
                  className="flex flex-col items-center gap-1"
                  initial={{ scale: 0, rotate: 180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", delay: 0.2 }}
                >
                  <motion.div 
                    className={`text-3xl font-black ${averageProfit > 0 ? 'text-green-400' : 'text-red-400'}`}
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                  >
                    {averageProfit > 0 ? '+' : ''}{averageProfit.toFixed(1)}%
                  </motion.div>
                  <span className="text-xs text-white/50">Avg Profit</span>
                  <motion.div 
                    className={`h-1 w-12 rounded-full ${averageProfit > 0 ? 'bg-green-400/30' : 'bg-red-400/30'}`}
                    animate={{ scaleX: [0, 1, 0], opacity: [0, 1, 0] }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                  />
                </motion.div>
              )}
            </div>

            <DynamicDescription className="text-[10px] text-white/40 mt-1">
              Your LLMs & algos dominating the market
            </DynamicDescription>
          </motion.div>
        )}
      </AnimatePresence>
    </DynamicContainer>
  );
};

