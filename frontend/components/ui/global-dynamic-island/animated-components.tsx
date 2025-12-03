"use client";

import { motion } from "motion/react";

/**
 * Animated pulse ring component for connection indicators
 */
export const PulseRing = ({ 
  color = "hsl(var(--brand-flame))", 
  delay = 0 
}: { 
  color?: string; 
  delay?: number;
}) => (
  <motion.div
    className="absolute inset-0 rounded-full"
    style={{ borderColor: color, borderWidth: 1 }}
    initial={{ scale: 1, opacity: 0.8 }}
    animate={{ scale: 2.5, opacity: 0 }}
    transition={{
      duration: 2,
      repeat: Infinity,
      delay,
      ease: "easeOut",
    }}
  />
);

/**
 * Animated waveform for analyzing states
 */
export const Waveform = ({ color = "white" }: { color?: string }) => (
  <div className="flex items-center gap-0.5 h-4">
    {[...Array(5)].map((_, i) => (
      <motion.div
        key={i}
        className="w-0.5 rounded-full"
        style={{ backgroundColor: color }}
        initial={{ height: 4 }}
        animate={{ height: [4, 16, 4] }}
        transition={{
          duration: 0.8,
          repeat: Infinity,
          delay: i * 0.1,
          ease: "easeInOut",
        }}
      />
    ))}
  </div>
);

