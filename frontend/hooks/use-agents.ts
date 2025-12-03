import { useState, useEffect, useCallback } from "react";
import { useApi as useApiRequest } from "@/lib/api";

export interface CustomIndicator {
    name: string;
    formula: string;
}

export interface Agent {
    id: string;
    name: string;
    mode: "monk" | "omni";
    model: string;
    api_key_id?: string;
    api_key_masked: string;
    indicators: string[];
    custom_indicators?: CustomIndicator[];
    strategy_prompt: string;
    tests_run: number;
    best_pnl: number;
    total_profitable_tests: number;
    avg_win_rate: number;
    avg_drawdown: number;
    created_at: string;
    updated_at: string;
}

export interface AgentCreate {
    name: string;
    mode: "monk" | "omni";
    model: string;
    api_key_id: string;
    indicators: string[];
    custom_indicators?: CustomIndicator[];
    strategy_prompt: string;
}

export interface AgentUpdate {
    name?: string;
    mode?: "monk" | "omni";
    model?: string;
    api_key_id?: string;
    indicators?: string[];
    custom_indicators?: CustomIndicator[];
    strategy_prompt?: string;
}

export interface AgentFilters {
    search?: string;
    mode?: "monk" | "omni";
    model?: string;
    sort?: "newest" | "oldest" | "performance" | "tests" | "alpha";
    include_archived?: boolean;
}

export interface AgentStats {
    id: string;
    tests_run: number;
    best_pnl: number;
    worst_pnl: number;
    total_profitable_tests: number;
    total_losing_tests: number;
    avg_win_rate: number;
    avg_profit_factor: number;
    avg_drawdown: number;
    avg_sharpe_ratio: number;
}

export function useAgents(initialFilters?: AgentFilters) {
    const { request } = useApiRequest();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<AgentFilters>(initialFilters || {});
    const [total, setTotal] = useState(0);

    // Helper methods for different HTTP operations
    const get = useCallback(
        async <T,>(endpoint: string) => {
            return request<T>(endpoint, { method: "GET" });
        },
        [request]
    );

    const post = useCallback(
        async <T,>(endpoint: string, body?: any) => {
            return request<T>(endpoint, { method: "POST", body });
        },
        [request]
    );

    const put = useCallback(
        async <T,>(endpoint: string, body?: any) => {
            return request<T>(endpoint, { method: "PUT", body });
        },
        [request]
    );

    const del = useCallback(
        async (endpoint: string) => {
            return request(endpoint, { method: "DELETE" });
        },
        [request]
    );

    // Build query string from filters
    const buildQueryString = useCallback((filters: AgentFilters) => {
        const params = new URLSearchParams();
        if (filters.search) params.append("search", filters.search);
        if (filters.mode) params.append("mode", filters.mode);
        if (filters.model) params.append("model", filters.model);
        if (filters.sort) params.append("sort", filters.sort);
        if (filters.include_archived !== undefined) {
            params.append("include_archived", String(filters.include_archived));
        }
        return params.toString() ? `?${params.toString()}` : "";
    }, []);

    // Fetch agents with filters
    const fetchAgents = useCallback(
        async (customFilters?: AgentFilters) => {
            console.log("fetchAgents called", { customFilters, filters });
            try {
                setIsLoading(true);
                setError(null);
                const activeFilters = customFilters || filters;
                const queryString = buildQueryString(activeFilters);
                console.log("Fetching from:", `/api/agents${queryString}`);
                const response = await get<{ agents: Agent[]; total: number }>(
                    `/api/agents${queryString}`
                );
                console.log("Fetch success:", response);
                setAgents(response.agents);
                setTotal(response.total);
            } catch (err) {
                console.error("Fetch error:", err);
                setError(err instanceof Error ? err.message : "Failed to fetch agents");
            } finally {
                setIsLoading(false);
            }
        },
        [get, buildQueryString] // Removed filters from dependencies
    );

    // Auto-fetch on mount only
    useEffect(() => {
        fetchAgents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Empty array - only fetch on mount

    // Refetch when filters change
    useEffect(() => {
        if (filters.search !== undefined || filters.mode || filters.model || filters.sort) {
            fetchAgents();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters.search, filters.mode, filters.model, filters.sort]);

    // Update filters and refetch
    const updateFilters = useCallback(
        (newFilters: Partial<AgentFilters>) => {
            setFilters((prev) => ({ ...prev, ...newFilters }));
        },
        []
    );

    // Create new agent
    const createAgent = useCallback(
        async (data: AgentCreate) => {
            try {
                setError(null);
                const response = await post<{ agent: Agent; message: string }>(
                    "/api/agents",
                    data
                );
                await fetchAgents(); // Refresh the list
                return response.agent;
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to create agent";
                setError(errorMessage);
                throw err;
            }
        },
        [post, fetchAgents]
    );

    // Get single agent
    const getAgent = useCallback(
        async (id: string) => {
            try {
                setError(null);
                // Backend returns the agent object directly
                const response = await get<Agent>(`/api/agents/${id}`);
                return response;
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to fetch agent";
                setError(errorMessage);
                throw err;
            }
        },
        [get]
    );

    // Update agent
    const updateAgent = useCallback(
        async (id: string, data: AgentUpdate) => {
            try {
                setError(null);
                // Backend returns the updated agent object directly
                const response = await put<Agent>(
                    `/api/agents/${id}`,
                    data
                );
                await fetchAgents(); // Refresh the list
                return response;
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to update agent";
                setError(errorMessage);
                throw err;
            }
        },
        [put, fetchAgents]
    );

    // Delete agent (archive by default)
    const deleteAgent = useCallback(
        async (id: string, archive: boolean = true) => {
            try {
                setError(null);
                const queryString = archive ? "?archive=true" : "?archive=false";
                await del(`/api/agents/${id}${queryString}`);
                await fetchAgents(); // Refresh the list
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to delete agent";
                setError(errorMessage);
                throw err;
            }
        },
        [del, fetchAgents]
    );

    // Duplicate agent
    const duplicateAgent = useCallback(
        async (id: string, newName: string) => {
            try {
                setError(null);
                const response = await post<{ agent: Agent; message: string }>(
                    `/api/agents/${id}/duplicate`,
                    { new_name: newName }
                );
                await fetchAgents(); // Refresh the list
                return response.agent;
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to duplicate agent";
                setError(errorMessage);
                throw err;
            }
        },
        [post, fetchAgents]
    );

    // Get agent stats
    const getAgentStats = useCallback(
        async (id: string) => {
            try {
                setError(null);
                const response = await get<{ stats: AgentStats }>(
                    `/api/agents/${id}/stats`
                );
                return response.stats;
            } catch (err) {
                const errorMessage =
                    err instanceof Error ? err.message : "Failed to fetch agent stats";
                setError(errorMessage);
                throw err;
            }
        },
        [get]
    );

    return {
        agents,
        total,
        isLoading,
        error,
        filters,
        updateFilters,
        createAgent,
        getAgent,
        updateAgent,
        deleteAgent,
        duplicateAgent,
        getAgentStats,
        refetch: fetchAgents,
    };
}
