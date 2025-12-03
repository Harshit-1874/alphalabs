"use client";

import { useEffect } from "react";
import { useDynamicIslandSize } from "@/components/ui/dynamic-island";
import type { IslandMode } from "@/lib/stores/dynamic-island-store";
import { MODE_TO_SIZE } from "./constants";

interface IslandSizeControllerProps {
  mode: IslandMode;
}

/**
 * Component that syncs store state with Dynamic Island size
 */
export const IslandSizeController = ({ mode }: IslandSizeControllerProps) => {
  const { setSize } = useDynamicIslandSize();
  
  useEffect(() => {
    const targetSize = MODE_TO_SIZE[mode];
    setSize(targetSize);
  }, [mode, setSize]);
  
  return null;
};

