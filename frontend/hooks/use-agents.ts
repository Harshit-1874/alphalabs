import { useCallback, useEffect, useRef } from "react";
import { useApiClient } from "@/lib/api";
import { useAgentsStore } from "@/lib/stores/agents-store";
import type { Agent, AgentMode } from "@/types/agent";

export interface CustomIndicator {
  name: string;
  formula: string;
}

export interface AgentCreate {
  name: string;
  mode: AgentMode;
  model: string;
  api_key_id: string;
  indicators: string[];
  custom_indicators?: CustomIndicator[];
  strategy_prompt: string;
}

export interface AgentUpdate {
  name?: string;
  mode?: AgentMode;
  model?: string;
  api_key_id?: string;
  indicators?: string[];
  custom_indicators?: CustomIndicator[];
  strategy_prompt?: string;
}

export type AgentFilters = {
  search?: string;
  mode?: AgentMode;
  model?: string;
  sort?: "newest" | "oldest" | "performance" | "tests" | "alpha";
};

const mapAgentResponse = (payload: any): Agent => ({
  id: payload.id,
  name: payload.name,
  model: payload.model,
  mode: payload.mode,
  indicators: payload.indicators ?? [],
  customIndicators: payload.custom_indicators ?? [],
  strategyPrompt: payload.strategy_prompt ?? "",
  apiKeyMasked: payload.api_key_masked ?? "",
  testsRun: payload.tests_run ?? 0,
  bestPnL: payload.best_pnl ?? null,
  createdAt: payload.created_at ? new Date(payload.created_at) : new Date(),
  updatedAt: payload.updated_at ? new Date(payload.updated_at) : new Date(),
  isArchived: payload.is_archived ?? false,
  stats: {
    totalTests: payload.tests_run ?? 0,
    profitableTests: payload.total_profitable_tests ?? 0,
    bestPnL: payload.best_pnl ?? 0,
    avgWinRate: payload.avg_win_rate ?? 0,
    avgDrawdown: payload.avg_drawdown ?? 0,
  },
});

const buildQueryString = (filters: AgentFilters) => {
  const params = new URLSearchParams();
  if (filters.search) params.append("search", filters.search);
  if (filters.mode) params.append("mode", filters.mode);
  if (filters.model) params.append("model", filters.model);
  if (filters.sort) params.append("sort", filters.sort);
  return params.toString() ? `?${params.toString()}` : "";
};

export function useAgents(initialFilters?: AgentFilters, includeArchived = false) {
  const { get, post, put, del } = useApiClient();
  const {
    agents,
    total,
    filters,
    isLoading,
    error,
    lastQueryKey,
    setAgents,
    setTotal,
    setLoading,
    setError,
    setFilters,
    setSearchQuery,
    toggleModelFilter,
    toggleModeFilter,
    setSortBy,
    clearFilters,
    filteredAgents,
    setLastQueryKey,
  } = useAgentsStore((state) => state);

  const appliedInitialFilters = useRef(false);
  useEffect(() => {
    if (initialFilters && !appliedInitialFilters.current) {
      setFilters(initialFilters);
      appliedInitialFilters.current = true;
    }
  }, [initialFilters, setFilters]);

  const fetchAgents = useCallback(async (force = false) => {
    // Get current state values from store to check if we should skip
    const storeState = useAgentsStore.getState();
    
    // Prevent concurrent fetches
    if (storeState.isLoading && !force) {
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      // Get filters from store to ensure we have the latest
      const currentFilters = storeState.filters;
      const queryString = buildQueryString({
        search: currentFilters.search,
        mode: currentFilters.mode,
        model: currentFilters.model,
        sort: currentFilters.sort,
      });
      const archivedParam = includeArchived ? "&include_archived=true" : "";
      const fullQuery = queryString ? `${queryString}${archivedParam}` : archivedParam ? `?${archivedParam.slice(1)}` : "";
      // Create a full query key that matches the actual query sent to API
      const fullQueryKey = fullQuery;
      
      const currentLastQueryKey = storeState.lastQueryKey;
      const currentAgents = storeState.agents;
      
      // Only skip if not forcing and query key matches and we have data
      if (!force && currentLastQueryKey === fullQueryKey && currentAgents.length > 0) {
        setLoading(false);
        return;
      }
      setLastQueryKey(fullQueryKey);
      const response = await get<{ agents: any[]; total: number }>(
        `/api/agents${fullQuery}`
      );
      setAgents(response.agents.map(mapAgentResponse));
      setTotal(response.total ?? response.agents.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch agents");
    } finally {
      setLoading(false);
    }
  }, [get, setAgents, setError, setLastQueryKey, setLoading, setTotal, includeArchived]);

  // Track previous values to prevent unnecessary fetches
  const prevValuesRef = useRef({ includeArchived, filters });
  
  useEffect(() => {
    const storeState = useAgentsStore.getState();
    
    // Skip if already loading
    if (storeState.isLoading) {
      return;
    }
    
    // Check if anything actually changed
    const includeArchivedChanged = prevValuesRef.current.includeArchived !== includeArchived;
    const filtersChanged = 
      prevValuesRef.current.filters.search !== filters.search ||
      prevValuesRef.current.filters.mode !== filters.mode ||
      prevValuesRef.current.filters.model !== filters.model ||
      prevValuesRef.current.filters.sort !== filters.sort;
    
    // Update ref
    prevValuesRef.current = { includeArchived, filters };
    
    // Only fetch if something changed
    if (includeArchivedChanged || filtersChanged) {
      void fetchAgents(includeArchivedChanged);
    } else {
      // On mount, fetch if we don't have data
      const hasData = storeState.agents.length > 0 && storeState.lastQueryKey;
      if (!hasData) {
        void fetchAgents();
      }
    }
  }, [includeArchived, filters.search, filters.mode, filters.model, filters.sort, fetchAgents]);

  const updateFilters = useCallback(
    (partial: AgentFilters) => {
      setFilters(partial);
    },
    [setFilters]
  );

  const createAgent = useCallback(
    async (data: AgentCreate) => {
      setError(null);
      try {
        const response = await post<{ agent: Agent; message: string }>(
          "/api/agents",
          data
        );
        // Force refresh to get the new agent
        await fetchAgents(true);
        return response.agent;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to create agent";
        setError(errorMessage);
        throw err;
      }
    },
    [fetchAgents, post, setError]
  );

  const getAgent = useCallback(
    async (id: string) => {
      setError(null);
      try {
        return await get<Agent>(`/api/agents/${id}`);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch agent";
        setError(errorMessage);
        throw err;
      }
    },
    [get, setError]
  );

  const updateAgent = useCallback(
    async (id: string, data: AgentUpdate) => {
      setError(null);
      try {
        const response = await put<Agent>(`/api/agents/${id}`, data);
        // Force refresh to get updated agent
        await fetchAgents(true);
        return response;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to update agent";
        setError(errorMessage);
        throw err;
      }
    },
    [fetchAgents, put, setError]
  );

  const deleteAgent = useCallback(
    async (id: string, archive: boolean = true) => {
      setError(null);
      try {
        const queryString = archive ? "?archive=true" : "?archive=false";
        await del(`/api/agents/${id}${queryString}`);
        // Force refresh to remove deleted agent
        await fetchAgents(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to delete agent";
        setError(errorMessage);
        throw err;
      }
    },
    [del, fetchAgents, setError]
  );

  const duplicateAgent = useCallback(
    async (id: string, newName: string) => {
      setError(null);
      try {
        const response = await post<{ agent: Agent; message: string }>(
          `/api/agents/${id}/duplicate`,
          { new_name: newName }
        );
        // Force refresh to get the duplicated agent
        await fetchAgents(true);
        return response.agent;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to duplicate agent";
        setError(errorMessage);
        throw err;
      }
    },
    [fetchAgents, post, setError]
  );

  const restoreAgent = useCallback(
    async (id: string) => {
      setError(null);
      try {
        await post<{ message: string; id: string }>(`/api/agents/${id}/restore`);
        // Force refresh to get the restored agent
        await fetchAgents(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to restore agent";
        setError(errorMessage);
        throw err;
      }
    },
    [fetchAgents, post, setError]
  );

  const getAgentStats = useCallback(
    async (id: string) => {
      setError(null);
      try {
        const response = await get<{ stats: any }>(`/api/agents/${id}/stats`);
        return response.stats;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch agent stats";
        setError(errorMessage);
        throw err;
      }
    },
    [get, setError]
  );

  return {
    agents,
    total,
    isLoading,
    error,
    filters,
    updateFilters,
    setSearchQuery,
    toggleModelFilter,
    toggleModeFilter,
    setSortBy,
    clearFilters,
    filteredAgents: filteredAgents(),
    createAgent,
    getAgent,
    updateAgent,
    deleteAgent,
    duplicateAgent,
    restoreAgent,
    getAgentStats,
    refetch: () => fetchAgents(true),
  };
}
