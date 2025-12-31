import { useSessionsStore } from "@/lib/stores/sessions-store";

export interface ForwardSession {
  id: string;
  agentId: string;
  agentName: string;
  asset: string;
  status: "running" | "paused" | "initializing";
  startedAt: string;
  durationDisplay: string;
  currentPnlPct: number;
  tradesCount: number;
  winRate: number;
}

/**
 * Hook to access forward sessions from the centralized store.
 * Sessions are fetched by ActiveSessionsProvider, so this hook just reads from the store.
 * @param pollInterval - Deprecated, kept for API compatibility. Polling is handled by ActiveSessionsProvider.
 */
export function useForwardSessions(_pollInterval = 15000) {
  const forwardSessions = useSessionsStore((state) => state.forwardSessions);
  const isLoading = useSessionsStore((state) => state.isLoading);
  const error = useSessionsStore((state) => state.error);
  const triggerRefresh = useSessionsStore((state) => state.triggerRefresh);

  return {
    sessions: forwardSessions,
    isLoading,
    error,
    refetch: triggerRefresh,
  };
}

