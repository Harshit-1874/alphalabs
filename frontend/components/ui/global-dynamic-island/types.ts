import type {
  NarratorData,
  TradeData,
  AlphaData,
  CelebrationData,
  ConnectionData,
  LiveSessionData,
  AnalyzingData,
} from "@/lib/stores/dynamic-island-store";

/**
 * Props for the GlobalDynamicIsland component
 */
export interface GlobalDynamicIslandProps {
  /** Custom class for the island container */
  className?: string;
  /** Whether to show confetti on celebration */
  enableConfetti?: boolean;
  /** Confetti colors for profit celebration */
  confettiColors?: string[];
  /** Custom idle content */
  idleContent?: React.ReactNode;
  /** Custom render for narrator state */
  renderNarrator?: (data: NarratorData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for trade state */
  renderTrade?: (data: TradeData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for alpha state */
  renderAlpha?: (data: AlphaData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for celebration state */
  renderCelebration?: (data: CelebrationData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for connection state */
  renderConnection?: (data: ConnectionData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for analyzing state */
  renderAnalyzing?: (data?: AnalyzingData, isExpanded?: boolean) => React.ReactNode;
  /** Custom render for live session state */
  renderLiveSession?: (data: LiveSessionData, isExpanded?: boolean) => React.ReactNode;
}

