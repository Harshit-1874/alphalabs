import { useSessionsStore } from "@/lib/stores/sessions-store";
import type { ForwardSession } from "./use-forward-sessions";

/**
 * Hook to access backtest sessions from the centralized store.
 * Sessions are fetched by ActiveSessionsProvider, so this hook just reads from the store.
 * @param pollInterval - Deprecated, kept for API compatibility. Polling is handled by ActiveSessionsProvider.
 */
export function useBacktestSessions(_pollInterval = 15000) {
  const backtestSessions = useSessionsStore((state) => state.backtestSessions);
  const isLoading = useSessionsStore((state) => state.isLoading);
  const error = useSessionsStore((state) => state.error);
  const triggerRefresh = useSessionsStore((state) => state.triggerRefresh);

  return {
    sessions: backtestSessions,
    isLoading,
    error,
    refetch: triggerRefresh,
  };
}

