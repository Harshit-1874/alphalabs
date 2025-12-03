"use client";

import { useState } from "react";
import { Eye, EyeOff, ExternalLink, Check, X, Loader2 } from "lucide-react";
import { Atom, Lightning, Cube } from "@phosphor-icons/react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { cn } from "@/lib/utils";
import type { AgentFormData, StepModelApiProps } from "@/types/agent";

const models = [
  {
    id: "deepseek-r1",
    name: "DeepSeek-R1",
    icon: Atom,
    bestFor: "Logical reasoning, math-heavy strategies",
    meta: "Speed: Fast • Context: 64K tokens",
  },
  {
    id: "claude-3.5",
    name: "Claude 3.5 Sonnet",
    icon: Lightning,
    bestFor: "Nuanced analysis, complex reasoning",
    meta: "Speed: Medium • Context: 200K tokens",
  },
  {
    id: "gemini-1.5-pro",
    name: "Gemini 1.5 Pro",
    icon: Cube,
    bestFor: "Large context, multi-modal analysis",
    meta: "Speed: Fast • Context: 1M tokens",
  },
];

type ValidationStatus = "idle" | "validating" | "valid" | "invalid";

export function StepModelApi({ formData, updateFormData }: StepModelApiProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>("idle");

  const validateApiKey = async () => {
    if (!formData.apiKey) return;
    
    setValidationStatus("validating");
    // Simulate API validation
    await new Promise((resolve) => setTimeout(resolve, 1500));
    
    // Mock validation - in real app call API
    const isValid = formData.apiKey.startsWith("sk-or-");
    setValidationStatus(isValid ? "valid" : "invalid");
  };

  const selectedModel = models.find((m) => m.id === formData.model);

  return (
    <div className="space-y-6">
      {/* Model Selection */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">
          Select AI Model <span className="text-destructive">*</span>
        </Label>
        <AnimatedSelect
          value={formData.model}
          onValueChange={(value) => updateFormData({ model: value })}
        >
          <AnimatedSelectTrigger className="w-full h-10">
            {selectedModel ? (
              <span className="flex items-center gap-2">
                <selectedModel.icon size={18} weight="duotone" className="text-primary" />
                <span>{selectedModel.name}</span>
              </span>
            ) : (
              <AnimatedSelectValue placeholder="Select a model..." />
            )}
          </AnimatedSelectTrigger>
          <AnimatedSelectContent>
            {models.map((model) => (
              <AnimatedSelectItem key={model.id} value={model.id} className="py-3">
                <div className="flex items-center gap-2">
                  <model.icon size={18} weight="duotone" className="text-primary" />
                  <span className="font-medium">{model.name}</span>
                </div>
              </AnimatedSelectItem>
            ))}
          </AnimatedSelectContent>
        </AnimatedSelect>
      </div>

      {/* Selected Model Info - Shows full details */}
      {selectedModel && (
        <div className="rounded-lg border border-border/50 bg-muted/20 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <selectedModel.icon size={28} weight="duotone" />
            </div>
            <div>
              <p className="font-mono text-sm font-medium">{selectedModel.name}</p>
              <p className="text-xs text-muted-foreground">
                {selectedModel.bestFor}
              </p>
              <p className="text-xs text-muted-foreground/60">{selectedModel.meta}</p>
            </div>
          </div>
        </div>
      )}

      {/* API Key Input */}
      <div className="space-y-2">
        <Label htmlFor="apiKey" className="text-sm font-medium">
          OpenRouter API Key <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <Input
            id="apiKey"
            type={showApiKey ? "text" : "password"}
            placeholder="sk-or-v1-..."
            value={formData.apiKey}
            onChange={(e) => {
              updateFormData({ apiKey: e.target.value });
              setValidationStatus("idle");
            }}
            className="pr-20 font-mono input-glow"
          />
          <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setShowApiKey(!showApiKey)}
            >
              {showApiKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Your key is stored securely and only used for this agent.
          </p>
          <a
            href="https://openrouter.ai/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            Get one from OpenRouter
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>

      {/* Validation Status */}
      {formData.apiKey && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border p-3 text-sm",
            validationStatus === "valid" &&
              "border-[hsl(var(--accent-green)/0.3)] bg-[hsl(var(--accent-green)/0.1)]",
            validationStatus === "invalid" &&
              "border-[hsl(var(--accent-red)/0.3)] bg-[hsl(var(--accent-red)/0.1)]",
            (validationStatus === "idle" || validationStatus === "validating") &&
              "border-border/50 bg-muted/20"
          )}
        >
          {validationStatus === "validating" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">Validating...</span>
            </>
          )}
          {validationStatus === "valid" && (
            <>
              <Check className="h-4 w-4 text-[hsl(var(--accent-green))]" />
              <span className="text-[hsl(var(--accent-green))]">
                API Key Validated
              </span>
            </>
          )}
          {validationStatus === "invalid" && (
            <>
              <X className="h-4 w-4 text-[hsl(var(--accent-red))]" />
              <span className="text-[hsl(var(--accent-red))]">
                Invalid API Key
              </span>
            </>
          )}
          {validationStatus === "idle" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={validateApiKey}
            >
              Test
            </Button>
          )}
        </div>
      )}

      {/* Save to Account Checkbox */}
      <div className="flex items-center space-x-2">
        <Checkbox
          id="saveApiKey"
          checked={formData.saveApiKey}
          onCheckedChange={(checked) =>
            updateFormData({ saveApiKey: checked as boolean })
          }
        />
        <Label
          htmlFor="saveApiKey"
          className="text-sm font-normal text-muted-foreground"
        >
          Save this API key to my account for future agents
        </Label>
      </div>
    </div>
  );
}

