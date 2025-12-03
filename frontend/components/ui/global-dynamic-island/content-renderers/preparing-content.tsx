"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { 
  Target, Zap, Rocket, Shield, Radio, Wifi, Activity,
  Cpu, Database, Sparkles
} from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";

interface PreparingContentProps {
  type: "backtest" | "forward";
  isExpanded?: boolean;
}

// Finance movie quotes for entertainment while preparing
const FINANCE_QUOTES = [
  { quote: "Be fearful when others are greedy, greedy when others are fearful", source: "Buffett" },
  { quote: "The market can stay irrational longer than you can stay solvent", source: "Keynes" },
  { quote: "Greed, for lack of a better word, is good", source: "Wall Street" },
  { quote: "It's not how much you make, it's how much you keep", source: "Kiyosaki" },
  { quote: "In this building, it's kill or be killed", source: "Wolf of Wall Street" },
  { quote: "I'm not uncertain. I'm just wrong", source: "The Big Short" },
  { quote: "Risk comes from not knowing what you're doing", source: "Buffett" },
];

const BACKTEST_STATES = [
  { icon: Target, text: "Targeting", subtext: "Historical", color: "#f59e0b" },
  { icon: Database, text: "Loading", subtext: "Candles", color: "#22c55e" },
  { icon: Cpu, text: "Calibrating", subtext: "AI", color: "#3b82f6" },
  { icon: Shield, text: "Checking", subtext: "Risk", color: "#a855f7" },
  { icon: Rocket, text: "Ready!", subtext: "Launch", color: "#E8400D" },
];

const FORWARD_STATES = [
  { icon: Radio, text: "Connecting", subtext: "Markets", color: "#a855f7" },
  { icon: Wifi, text: "Locked", subtext: "Signal", color: "#22c55e" },
  { icon: Cpu, text: "Warming", subtext: "AI", color: "#3b82f6" },
  { icon: Zap, text: "Armed", subtext: "Ready", color: "#f59e0b" },
  { icon: Activity, text: "Loaded", subtext: "Go!", color: "#E8400D" },
];

export const PreparingContent = ({ type, isExpanded }: PreparingContentProps) => {
  const [stateIndex, setStateIndex] = useState(0);
  const [quoteIndex, setQuoteIndex] = useState(() => Math.floor(Math.random() * FINANCE_QUOTES.length));
  const states = type === "backtest" ? BACKTEST_STATES : FORWARD_STATES;
  const current = states[stateIndex];
  const currentQuote = FINANCE_QUOTES[quoteIndex];
  const Icon = current.icon;
  const isBacktest = type === "backtest";

  useEffect(() => {
    const interval = setInterval(() => {
      setStateIndex((prev) => (prev + 1) % states.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [states.length]);

  useEffect(() => {
    const interval = setInterval(() => {
      setQuoteIndex((prev) => (prev + 1) % FINANCE_QUOTES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Compact view
  if (!isExpanded) {
    return (
      <DynamicContainer className="flex h-full w-full items-center justify-center pt-1">
        <div className="flex items-center gap-2.5 px-3">
          {/* Icon */}
          <motion.div
            className="relative"
            key={stateIndex}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 25 }}
          >
            <motion.div
              className="flex h-7 w-7 items-center justify-center rounded-lg"
              style={{ backgroundColor: `${current.color}20` }}
              animate={{ 
                boxShadow: [
                  `0 0 0px ${current.color}`,
                  `0 0 12px ${current.color}`,
                  `0 0 0px ${current.color}`,
                ]
              }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <Icon className="h-3.5 w-3.5" style={{ color: current.color }} />
            </motion.div>
            
            <motion.div
              className="absolute h-1 w-1 rounded-full"
              style={{ backgroundColor: current.color }}
              animate={{
                rotate: 360,
                x: [0, 10, 0, -10, 0],
                y: [-10, 0, 10, 0, -10],
              }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            />
          </motion.div>

          {/* Text */}
          <motion.div
            key={`text-${stateIndex}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-1.5"
          >
            <span className="text-[13px] font-bold text-white">
              {current.text}
            </span>
            <motion.span 
              className="text-[11px] font-medium"
              style={{ color: current.color }}
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              {current.subtext}
            </motion.span>
          </motion.div>

          {/* Dots */}
          <div className="flex items-center gap-0.5">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="h-1 w-1 rounded-full"
                style={{ backgroundColor: current.color }}
                animate={{ scale: [1, 1.4, 1], opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
              />
            ))}
          </div>
        </div>
      </DynamicContainer>
    );
  }

  // Expanded view
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
              style={{ backgroundColor: current.color }}
              animate={{ 
                scale: [1, 1.3, 1],
                boxShadow: [
                  `0 0 0px ${current.color}`,
                  `0 0 10px ${current.color}`,
                  `0 0 0px ${current.color}`,
                ]
              }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" style={{ color: current.color }} />
            <span className="text-xs font-bold text-white">
              {isBacktest ? "Backtest" : "Forward"}
            </span>
            <motion.span 
              className="text-[10px] font-semibold uppercase"
              style={{ color: current.color }}
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              Prep
            </motion.span>
          </div>
        </div>
        
        <motion.div 
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-full border"
          style={{ 
            backgroundColor: `${current.color}15`,
            borderColor: `${current.color}30`,
          }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Zap className="h-3 w-3" style={{ color: current.color }} />
          <span className="text-[10px] font-semibold" style={{ color: current.color }}>
            {isBacktest ? "Sim" : "Live"}
          </span>
        </motion.div>
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
            backgroundColor: `${current.color}10`,
            borderColor: `${current.color}40`,
          }}
          key={stateIndex}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <motion.div
            className="absolute inset-0"
            style={{ 
              background: `radial-gradient(circle at 80% 20%, ${current.color}20, transparent 60%)`,
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
                key={current.text}
                initial={{ opacity: 0, y: 3 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {current.text}
              </motion.p>
              <p className="text-[9px] font-medium mt-0.5" style={{ color: current.color }}>
                {current.subtext}
              </p>
            </div>
            
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="p-1.5 rounded-lg"
              style={{ backgroundColor: `${current.color}15` }}
            >
              <Icon className="h-4 w-4" style={{ color: current.color }} />
            </motion.div>
          </div>
        </motion.div>

        {/* Mode Card */}
        <motion.div
          className="flex-1 rounded-xl bg-white/5 border border-white/10 px-2.5 py-2 flex items-center justify-center"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div className="flex items-center gap-2">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
            >
              {isBacktest ? (
                <Database className="h-4 w-4" style={{ color: current.color }} />
              ) : (
                <Activity className="h-4 w-4" style={{ color: current.color }} />
              )}
            </motion.div>
            <div>
              <p className="text-[8px] text-white/40 uppercase font-semibold">Mode</p>
              <p className="text-xs font-bold text-white leading-tight">
                {isBacktest ? "Hist" : "Live"}
              </p>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Quote - flex-1 to fill remaining space */}
      <motion.div
        className="flex-1 rounded-xl bg-white/5 border border-white/10 px-3 py-2 flex items-center"
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent"
          initial={{ x: "-100%" }}
          animate={{ x: "200%" }}
          transition={{ duration: 3, repeat: Infinity, repeatDelay: 2 }}
        />
        
        <div className="relative flex items-center gap-2.5 w-full">
          <Sparkles className="h-3.5 w-3.5 shrink-0" style={{ color: current.color }} />
          
          <motion.p 
            className="text-[11px] text-white/85 leading-relaxed italic flex-1 min-w-0"
            key={quoteIndex}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            &ldquo;{currentQuote.quote}&rdquo;
          </motion.p>
          
          <p 
            className="text-[10px] font-semibold shrink-0"
            style={{ color: current.color }}
          >
            — {currentQuote.source}
          </p>
        </div>
      </motion.div>
    </DynamicContainer>
  );
};
