import type { SizePresets } from "@/components/ui/dynamic-island";
import type { IslandMode } from "@/lib/stores/dynamic-island-store";

/**
 * Maps island modes to their corresponding size presets
 */
export const MODE_TO_SIZE: Record<IslandMode, SizePresets> = {
  hidden: "default",
  idle: "default",
  analyzing: "default", // Same size as idle/AI ready state
  narrator: "long", // Full AI thoughts display
  trade: "large",
  alpha: "tall",
  celebration: "tall",
  connection: "compact",
  liveSession: "default", // Small default size, expands to "medium" for richer dashboard
};

/**
 * Helper to check if current size is expanded from base size
 */
export const isExpandedSize = (currentSize: SizePresets, baseSize: SizePresets): boolean => {
  const sizeOrder: SizePresets[] = [
    "default",
    "compact",
    "compactLong",
    "large",
    "long",
    "tall",
    "medium",
    "ultra",
    "massive"
  ];
  const currentIndex = sizeOrder.indexOf(currentSize);
  const baseIndex = sizeOrder.indexOf(baseSize);
  return currentIndex > baseIndex;
};

