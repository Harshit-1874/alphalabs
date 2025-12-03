"use client";

import { useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import confetti from "canvas-confetti";
import {
  DynamicIsland,
  DynamicIslandProvider,
  useDynamicIslandSize,
} from "@/components/ui/dynamic-island";
import {
  useDynamicIslandStore,
  type CelebrationData,
} from "@/lib/stores/dynamic-island-store";
import { cn } from "@/lib/utils";
import { MODE_TO_SIZE, isExpandedSize } from "./constants";
import { IslandContent, type IslandContentProps } from "./island-content";
import { IslandSizeController } from "./island-size-controller";
import type { GlobalDynamicIslandProps } from "./types";

/**
 * Inner component that can access useDynamicIslandSize
 */
const IslandContentWithSize = ({
  mode,
  data,
  idleContent,
  renderNarrator,
  renderTrade,
  renderAlpha,
  renderCelebration,
  renderConnection,
  renderAnalyzing,
  renderLiveSession,
}: Omit<IslandContentProps, "isExpanded">) => {
  const { state } = useDynamicIslandSize();
  const baseSize = MODE_TO_SIZE[mode];
  const isExpanded = isExpandedSize(state.size, baseSize);
  
  return (
    <IslandContent
      mode={mode}
      data={data}
      isExpanded={isExpanded}
      idleContent={idleContent}
      renderNarrator={renderNarrator}
      renderTrade={renderTrade}
      renderAlpha={renderAlpha}
      renderCelebration={renderCelebration}
      renderConnection={renderConnection}
      renderAnalyzing={renderAnalyzing}
      renderLiveSession={renderLiveSession}
    />
  );
};

/**
 * Inner component with provider context
 */
const GlobalDynamicIslandInner = ({
  className,
  enableConfetti = true,
  confettiColors = ["#22c55e", "#86efac", "#fbbf24", "#E8400D"],
  idleContent,
  renderNarrator,
  renderTrade,
  renderAlpha,
  renderCelebration,
  renderConnection,
  renderAnalyzing,
  renderLiveSession,
}: GlobalDynamicIslandProps) => {
  const { mode, data, isVisible } = useDynamicIslandStore();
  
  // Fire confetti on celebration
  const fireConfetti = useCallback(() => {
    if (!enableConfetti) return;
    
    const celebrationData = data as CelebrationData;
    if (celebrationData?.pnl >= 0) {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.1, x: 0.5 },
        colors: confettiColors,
      });
    }
  }, [data, enableConfetti, confettiColors]);
  
  // Trigger confetti when entering celebration mode
  useEffect(() => {
    if (mode === "celebration") {
      fireConfetti();
    }
  }, [mode, fireConfetti]);
  
  return (
    <div
      className={cn(
        "fixed top-1 left-1/2 -translate-x-1/2 z-[9999]",
        "hidden sm:block", // Hide on mobile, show on tablet and up
        "sm:top-2", // Position on larger screens
        className
      )}
    >
      <AnimatePresence>
        {isVisible && mode !== "hidden" && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            <DynamicIsland id="global-dynamic-island">
              <IslandSizeController mode={mode} />
              <IslandContentWithSize
                mode={mode}
                data={data}
                idleContent={idleContent}
                renderNarrator={renderNarrator}
                renderTrade={renderTrade}
                renderAlpha={renderAlpha}
                renderCelebration={renderCelebration}
                renderConnection={renderConnection}
                renderAnalyzing={renderAnalyzing}
                renderLiveSession={renderLiveSession}
              />
            </DynamicIsland>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/**
 * Global Dynamic Island component - main entry point
 * Displays AI trading notifications in an iOS-inspired dynamic island UI
 */
export const GlobalDynamicIsland = (props: GlobalDynamicIslandProps) => {
  return (
    <DynamicIslandProvider initialSize="default">
      <GlobalDynamicIslandInner {...props} />
    </DynamicIslandProvider>
  );
};

export default GlobalDynamicIsland;

