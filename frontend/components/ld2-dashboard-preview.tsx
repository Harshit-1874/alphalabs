"use client";

import { motion } from "motion/react";

export default function LD2DashboardPreview() {
  return (
    <div className="container max-w-5xl mx-auto px-4 pt-16 relative z-10">
      {/* Text above dashboard */}
      <motion.div
        className="flex flex-col items-center space-y-3 pb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
      >
        <div className="flex items-center space-x-4 text-sm">
          <span className="text-black hover:opacity-70 transition-colors">
            AI-Powered Agents
          </span>
          <span className="text-black/40">
            •
          </span>
          <span className="text-black/60">
            Backtest & Forward Test
          </span>
          <span className="text-black/40">
            •
          </span>
          <span className="text-black hover:opacity-70 transition-colors">
            Performance Analytics
          </span>
        </div>
        <p className="text-sm text-black/50">
          Built for traders who demand precision and speed
        </p>
      </motion.div>

      {/* Dashboard Preview Video */}
      <motion.div
        className="w-full border border-gray-200 p-1 rounded-3xl bg-white"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.8 }}
      >
        <div className="relative w-full">
          <div className="relative w-full rounded-xl overflow-hidden border border-gray-100 shadow-2xl">
            <video
              src="/lpv.mp4"
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-center block rounded-2xl"
            />
          </div>

          {/* Gradient fade at bottom — REDUCED thickness */}
          <div className="absolute inset-x-0 bottom-0 h-[20%] bg-gradient-to-t from-white to-transparent rounded-b-2xl" />
        </div>
      </motion.div>

    </div>
  );
}

