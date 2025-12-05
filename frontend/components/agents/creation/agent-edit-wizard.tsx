"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { StepIdentity } from "./step-identity";
import { StepModelApi } from "./step-model-api";
import { StepDataBuffet } from "./step-data-buffet";
import { StepStrategyPrompt } from "./step-strategy-prompt";
import { useAgentsStore, useGlobalRefresh } from "@/lib/stores";
import { useAgents } from "@/hooks/use-agents";
import { useApiKeys } from "@/hooks/use-api-keys";
import type { AgentFormData } from "@/types/agent";

const steps = [
  { id: 1, name: "Identity", description: "Name & Mode" },
  { id: 2, name: "Model & API", description: "AI Configuration" },
  { id: 3, name: "Data Buffet", description: "Select Indicators" },
  { id: 4, name: "Strategy", description: "Trading Prompt" },
];

interface AgentEditWizardProps {
  agentId: string;
}

export function AgentEditWizard({ agentId }: AgentEditWizardProps) {
  const router = useRouter();
  const { agents } = useAgentsStore();
  const { updateAgent } = useAgents();
  const { createApiKey } = useApiKeys();
  const { refreshAll } = useGlobalRefresh();
  // Start at Data Buffet (step 3) when editing - most common edit
  const [currentStep, setCurrentStep] = useState(3);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState<AgentFormData>({
    name: "",
    mode: null,
    model: "",
    apiKey: "",
    saveApiKey: false,
    indicators: [],
    customIndicators: [],
    strategyPrompt: "",
  });

  // Load existing agent data
  useEffect(() => {
    const agent = agents.find((a) => a.id === agentId);
    if (agent) {
      setFormData({
        name: agent.name,
        mode: agent.mode,
        model: agent.model,
        apiKey: "", // Don't load actual key, show masked
        saveApiKey: false,
        indicators: agent.indicators.map((i) => i.toLowerCase()),
        customIndicators: agent.customIndicators || [],
        strategyPrompt: agent.strategyPrompt,
      });
    }
    setIsLoading(false);
  }, [agentId, agents]);

  const agent = agents.find((a) => a.id === agentId);

  const updateFormData = (updates: Partial<AgentFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return formData.name.length >= 2 && formData.mode !== null;
      case 2:
        // For edit, API key is optional (keep existing)
        return formData.model !== "";
      case 3:
        return formData.indicators.length > 0;
      case 4:
        return formData.strategyPrompt.length >= 50;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    } else {
      handleSave();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSave = async () => {
    if (isSaving) return;

    setIsSaving(true);
    try {
      let apiKeyId: string | undefined = undefined;

      // Check if formData.apiKey is provided
      if (formData.apiKey) {
        // If it's a new API key (starts with "sk-"), save it first
        if (formData.apiKey.startsWith("sk-")) {
          try {
            const newKey = await createApiKey({
              provider: "openrouter",
              api_key: formData.apiKey,
              label: formData.saveApiKey
                ? `${formData.name} - OpenRouter`
                : `Temp - ${formData.name}`,
              set_as_default: formData.saveApiKey,
            });
            apiKeyId = newKey.id;
          } catch (error) {
            toast.error("Failed to save API key. Please try again.");
            setIsSaving(false);
            return;
          }
        } else {
          // It's an existing API key UUID - use it directly
          apiKeyId = formData.apiKey;
        }
      }

      // Update the agent
      const updateData: any = {
        name: formData.name,
        mode: formData.mode!,
        model: formData.model,
        indicators: formData.indicators,
        custom_indicators: formData.customIndicators.length > 0 ? formData.customIndicators : undefined,
        strategy_prompt: formData.strategyPrompt,
      };

      // Include api_key_id if a key was provided (new or existing)
      if (apiKeyId) {
        updateData.api_key_id = apiKeyId;
      }

      await updateAgent(agentId, updateData);

      toast.success(`Agent "${formData.name}" updated successfully!`);
      refreshAll(); // Trigger global refresh for all stores
      router.push(`/dashboard/agents/${agentId}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to update agent";
      toast.error(errorMessage);
      console.error("Error updating agent:", error);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="text-center py-20">
          <h2 className="text-xl font-semibold">Agent not found</h2>
          <p className="mt-2 text-muted-foreground">
            The agent you're trying to edit doesn't exist.
          </p>
          <Button asChild className="mt-4">
            <Link href="/dashboard/agents">Back to Agents</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/dashboard/agents/${agentId}`}
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Agent
        </Link>
        <h1 className="font-mono text-2xl font-bold">Edit Agent: {agent.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Step {currentStep} of 4: {steps[currentStep - 1].name}
        </p>
      </div>

      {/* Progress Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors",
                    currentStep > step.id
                      ? "border-[hsl(var(--brand-flame))] bg-[hsl(var(--brand-flame))] text-white"
                      : currentStep === step.id
                        ? "border-[hsl(var(--brand-flame))] text-[hsl(var(--brand-flame))]"
                        : "border-border text-muted-foreground"
                  )}
                >
                  {currentStep > step.id ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    step.id
                  )}
                </div>
                <span
                  className={cn(
                    "mt-2 text-xs",
                    currentStep >= step.id
                      ? "text-foreground"
                      : "text-muted-foreground"
                  )}
                >
                  {step.name}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "mx-2 h-0.5 w-12 sm:w-20 lg:w-28",
                    currentStep > step.id
                      ? "bg-[hsl(var(--brand-flame))]"
                      : "bg-border"
                  )}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="mb-8 rounded-lg border border-border/50 bg-card/30 p-6">
        {currentStep === 1 && (
          <StepIdentity formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 2 && (
          <>
            <div className="mb-4 rounded-lg border border-[hsl(var(--accent-amber)/0.3)] bg-[hsl(var(--accent-amber)/0.1)] p-3">
              <p className="text-xs text-[hsl(var(--accent-amber))]">
                💡 Leave API key blank to keep the existing key
              </p>
            </div>
            <StepModelApi formData={formData} updateFormData={updateFormData} />
          </>
        )}
        {currentStep === 3 && (
          <StepDataBuffet formData={formData} updateFormData={updateFormData} />
        )}
        {currentStep === 4 && (
          <StepStrategyPrompt formData={formData} updateFormData={updateFormData} />
        )}
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.push(`/dashboard/agents/${agentId}`)}>
          Cancel
        </Button>
        <div className="flex gap-3">
          {currentStep > 1 && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
            </motion.div>
          )}
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
          >
            <Button
              onClick={handleNext}
              disabled={!canProceed() || isSaving}
              className={cn(
                currentStep === 4 &&
                "bg-[hsl(var(--brand-flame))] text-white hover:bg-[hsl(var(--brand-flame))]/90"
              )}
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : currentStep === 4 ? (
                "Save Changes ✓"
              ) : (
                "Continue →"
              )}
            </Button>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

