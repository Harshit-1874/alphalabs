import type {
  IslandMode,
  TradeData,
  NarratorData,
  CelebrationData,
  AlphaData,
  ConnectionData,
  LiveSessionData,
  AnalyzingData,
  PreparingData,
} from "@/lib/stores/dynamic-island-store";
import {
  IdleContent,
  AnalyzingContent,
  NarratorContent,
  TradeContent,
  AlphaContent,
  CelebrationContent,
  ConnectionContent,
  LiveSessionContent,
  PreparingContent,
} from "./content-renderers";

export interface IslandContentProps {
  mode: IslandMode;
  data: unknown;
  isExpanded?: boolean;
  totalAgents?: number;
  averageProfit?: number;
  idleContent?: React.ReactNode;
  renderNarrator?: (data: NarratorData, isExpanded?: boolean) => React.ReactNode;
  renderTrade?: (data: TradeData, isExpanded?: boolean) => React.ReactNode;
  renderAlpha?: (data: AlphaData, isExpanded?: boolean) => React.ReactNode;
  renderCelebration?: (data: CelebrationData, isExpanded?: boolean) => React.ReactNode;
  renderConnection?: (data: ConnectionData, isExpanded?: boolean) => React.ReactNode;
  renderAnalyzing?: (data?: AnalyzingData, isExpanded?: boolean) => React.ReactNode;
  renderLiveSession?: (data: LiveSessionData, isExpanded?: boolean) => React.ReactNode;
}

/**
 * Main content switcher component that renders the appropriate content based on mode
 */
export const IslandContent = ({
  mode,
  data,
  isExpanded,
  totalAgents,
  averageProfit,
  idleContent,
  renderNarrator,
  renderTrade,
  renderAlpha,
  renderCelebration,
  renderConnection,
  renderAnalyzing,
  renderLiveSession,
}: IslandContentProps) => {
  switch (mode) {
    case "idle":
      return idleContent || <IdleContent totalAgents={totalAgents} averageProfit={averageProfit} isExpanded={isExpanded} />;
      
    case "analyzing":
      if (renderAnalyzing) {
        return renderAnalyzing(data as AnalyzingData, isExpanded);
      }
      return <AnalyzingContent data={data as AnalyzingData} isExpanded={isExpanded} />;
      
    case "narrator":
      if (renderNarrator && data) {
        return renderNarrator(data as NarratorData, isExpanded);
      }
      return data ? <NarratorContent data={data as NarratorData} isExpanded={isExpanded} /> : null;
      
    case "trade":
      if (renderTrade && data) {
        return renderTrade(data as TradeData, isExpanded);
      }
      return data ? <TradeContent data={data as TradeData} isExpanded={isExpanded} /> : null;
      
    case "alpha":
      if (renderAlpha && data) {
        return renderAlpha(data as AlphaData, isExpanded);
      }
      return data ? <AlphaContent data={data as AlphaData} /> : null;
      
    case "celebration":
      if (renderCelebration && data) {
        return renderCelebration(data as CelebrationData, isExpanded);
      }
      return data ? <CelebrationContent data={data as CelebrationData} /> : null;
      
    case "connection":
      if (renderConnection && data) {
        return renderConnection(data as ConnectionData, isExpanded);
      }
      return data ? <ConnectionContent data={data as ConnectionData} /> : null;
      
    case "liveSession":
      if (renderLiveSession && data) {
        return renderLiveSession(data as LiveSessionData, isExpanded);
      }
      return data ? <LiveSessionContent data={data as LiveSessionData} isExpanded={isExpanded} /> : null;
      
    case "preparing":
      return data ? <PreparingContent type={(data as PreparingData).type} isExpanded={isExpanded} /> : null;
      
    case "hidden":
    default:
      return null;
  }
};

