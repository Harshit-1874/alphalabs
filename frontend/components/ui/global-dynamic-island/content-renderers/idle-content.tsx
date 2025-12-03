"use client";

import { motion } from "motion/react";
import { DynamicContainer } from "@/components/ui/dynamic-island";

export const IdleContent = () => (
  <DynamicContainer className="flex h-full w-full items-center justify-center">
    <div className="relative flex items-center gap-2">
      <div className="relative">
        <motion.div 
          className="h-2 w-2 rounded-full bg-[hsl(var(--brand-flame))]"
          animate={{ 
            scale: [1, 1.2, 1],
            boxShadow: [
              "0 0 0px hsl(var(--brand-flame))",
              "0 0 8px hsl(var(--brand-flame))",
              "0 0 0px hsl(var(--brand-flame))",
            ]
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <motion.span 
        className="text-xs font-medium text-white/70"
        initial={{ opacity: 0, x: -4 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
      >
        AI Ready
      </motion.span>
    </div>
  </DynamicContainer>
);

