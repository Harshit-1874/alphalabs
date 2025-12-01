import { useState, useEffect, useCallback } from "react";
import { useApi as useApiRequest } from "@/lib/api";

export interface ApiKey {
    id: string;
    provider: string;
    label: string;
    key_prefix: string;
    is_default: boolean;
    status: "valid" | "invalid" | "untested";
    last_used_at: string | null;
    used_by?: string[]; // Optional since backend may not return this
    created_at: string;
}

export interface ApiKeyCreate {
    provider: string;
    label?: string;
    api_key: string;
    set_as_default?: boolean;
}

export interface ApiKeyValidateResponse {
    valid: boolean;
    status: "valid" | "invalid";
    models_available?: string[];
    error?: string;
}

export function useApiKeys() {
    const { request } = useApiRequest();
    const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

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

    const del = useCallback(
        async (endpoint: string) => {
            return request(endpoint, { method: "DELETE" });
        },
        [request]
    );

    const fetchApiKeys = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const response = await get<{ api_keys: ApiKey[] }>("/api/api-keys");
            setApiKeys(response.api_keys);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to fetch API keys");
            console.error("Error fetching API keys:", err);
        } finally {
            setIsLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchApiKeys();
    }, [fetchApiKeys]);

    const createApiKey = useCallback(
        async (data: ApiKeyCreate) => {
            try {
                setError(null);
                const response = await post<{ api_key: ApiKey }>("/api/api-keys", data);
                await fetchApiKeys(); // Refresh the list
                return response.api_key;
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : "Failed to create API key";
                setError(errorMessage);
                throw err;
            }
        },
        [post, fetchApiKeys]
    );

    const validateApiKey = useCallback(
        async (id: string) => {
            try {
                setError(null);
                const response = await post<ApiKeyValidateResponse>(
                    `/api/api-keys/${id}/validate`,
                    {}
                );
                await fetchApiKeys(); // Refresh to get updated status
                return response;
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : "Failed to validate API key";
                setError(errorMessage);
                throw err;
            }
        },
        [post, fetchApiKeys]
    );

    const deleteApiKey = useCallback(
        async (id: string) => {
            try {
                setError(null);
                await del(`/api/api-keys/${id}`);
                await fetchApiKeys(); // Refresh the list
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : "Failed to delete API key";
                setError(errorMessage);
                throw err;
            }
        },
        [del, fetchApiKeys]
    );

    return {
        apiKeys,
        isLoading,
        error,
        createApiKey,
        validateApiKey,
        deleteApiKey,
        refetch: fetchApiKeys,
    };
}
