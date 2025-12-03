"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, ReactNode, useEffect } from "react";
import { cn } from "@/lib/utils";

interface ShiftCardProps {
  className?: string;
  topContent: ReactNode;
  topAnimateContent?: ReactNode;
  middleContent: ReactNode;
  bottomContent: ReactNode;
}

export function ShiftCard({
  className,
  topContent,
  topAnimateContent,
  middleContent,
  bottomContent,
}: ShiftCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile/touch device - only treat as mobile if BOTH small screen AND touch support
  useEffect(() => {
    const checkMobile = () => {
      const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const isSmallScreen = window.innerWidth < 768; // md breakpoint
      setIsMobile(hasTouch && isSmallScreen);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleInteraction = () => {
    if (isMobile) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <motion.div
      className={cn(
        "relative w-full overflow-hidden rounded-lg",
        isMobile ? "cursor-pointer" : "cursor-default",
        isExpanded && "z-20",
        className
      )}
      onHoverStart={() => !isMobile && setIsExpanded(true)}
      onHoverEnd={() => !isMobile && setIsExpanded(false)}
      onClick={handleInteraction}
      initial={false}
      layout
    >
      {/* Top Section */}
      <div className="relative">
        {topContent}
        <AnimatePresence>
          {isExpanded && topAnimateContent && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
            >
              {topAnimateContent}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Middle Section */}
      <div className="relative">
        {middleContent}
      </div>

      {/* Bottom Section (slides up and overlaps on hover/tap) */}
      <motion.div
        className="overflow-hidden"
        initial={{ height: 0, opacity: 0 }}
        animate={{
          height: isExpanded ? "auto" : 0,
          opacity: isExpanded ? 1 : 0,
        }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
      >
        {bottomContent}
      </motion.div>
    </motion.div>
  );
}

