// Agent Types

export type AgentMode = "monk" | "omni";

export interface Agent {
  id: string;
  name: string;
  model: string;
  mode: AgentMode;
  indicators: string[];
  customIndicators: CustomIndicator[];
  strategyPrompt: string;
  apiKeyMasked: string;
  testsRun: number;
  bestPnL: number | null;
  createdAt: Date;
  updatedAt: Date;
  // Stats for arena config
  stats: AgentStats;
}

export interface CustomIndicator {
  name: string;
  formula: string;
}

export interface AgentStats {
  totalTests: number;
  profitableTests: number;
  bestPnL: number;
  avgWinRate: number;
  avgDrawdown: number;
}

export interface AgentFormData {
  name: string;
  mode: AgentMode | null;
  model: string;
  apiKey: string;
  saveApiKey: boolean;
  indicators: string[];
  customIndicators: CustomIndicator[];
  strategyPrompt: string;
}

export interface AgentCardProps {
  agent: Agent;
  variant?: "grid" | "list";
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onDuplicate?: (id: string) => void;
}

export interface AgentListFilters {
  search: string;
  models: string[];
  modes: AgentMode[];
  sortBy: "newest" | "oldest" | "performance" | "tests" | "alpha";
}

// Component Props - Agent Creation Steps
export interface StepModelApiProps {
  formData: AgentFormData;
  updateFormData: (updates: Partial<AgentFormData>) => void;
}

export interface StepIdentityProps {
  formData: AgentFormData;
  updateFormData: (updates: Partial<AgentFormData>) => void;
  validationErrors?: Record<string, string>;
  setValidationErrors?: (errors: Record<string, string>) => void;
  currentAgentId?: string;
}

export interface StepDataBuffetProps {
  formData: AgentFormData;
  updateFormData: (updates: Partial<AgentFormData>) => void;
}

export interface StepStrategyPromptProps {
  formData: AgentFormData;
  updateFormData: (updates: Partial<AgentFormData>) => void;
}

export interface AgentDetailViewProps {
  agentId: string;
}

