import { useCallback, useEffect, useState } from "react";
import { useApiClient } from "@/lib/api";

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description: string;
  contextWindow: string;
  capabilities: string[];
  tags?: string[];
  isMultimodal?: boolean;
  isFree?: boolean;  // True for free tier models, false for paid models
}

type ApiModel = {
  id: string;
  name: string;
  provider: string;
  description: string;
  context_window: string;
  capabilities: string[];
  tags?: string[];
  is_multimodal?: boolean;
  is_free?: boolean;  // True for free tier models, false for paid models
};

export function useModels() {
  const { get } = useApiClient();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await get<ApiModel[]>("/api/models");
      if (!Array.isArray(response)) {
        throw new Error("Invalid model payload");
      }

      setModels(
        response.map((model) => ({
          id: model.id,
          name: model.name,
          provider: model.provider,
          description: model.description,
          contextWindow: model.context_window,
          capabilities: model.capabilities,
          tags: model.tags,
          isMultimodal: model.is_multimodal,
          isFree: model.is_free,
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models");
    } finally {
      setIsLoading(false);
    }
  }, [get]);

  useEffect(() => {
    void fetchModels();
  }, [fetchModels]);

  return {
    models,
    isLoading,
    error,
    refetch: fetchModels,
  };
}

