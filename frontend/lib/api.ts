import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

type RequestMethod = "GET" | "POST" | "PUT" | "DELETE";

interface ApiOptions {
    method?: RequestMethod;
    body?: any;
    headers?: Record<string, string>;
}

export async function apiRequest<T>(
    endpoint: string,
    token: string | null,
    options: ApiOptions = {}
): Promise<T> {
    const { method = "GET", body, headers = {} } = options;

    const config: RequestInit = {
        method,
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
    };

    if (token) {
        (config.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }

    if (body) {
        config.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request failed: ${response.statusText}`);
    }

    return response.json();
}

export const useApi = () => {
    const { getToken } = useAuth();

    const request = useCallback(async <T>(endpoint: string, options: ApiOptions = {}) => {
        const token = await getToken();
        return apiRequest<T>(endpoint, token, options);
    }, [getToken]);

    return { request };
};
