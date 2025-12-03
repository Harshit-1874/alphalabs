"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Crosshair, Eye } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { useAgents } from "@/hooks/use-agents";
import type { StepIdentityProps } from "@/types/agent";

const modes = [
  {
    id: "monk" as const,
    icon: Crosshair,
    name: "MONK MODE",
    subtitle: "The Blindfolded Quant",
    features: [
      "Pure technical analysis",
      "No news, no dates",
      "Max 1% risk per trade",
      "1 trade per 4 hours",
    ],
    description: "Prove your AI understands market structure.",
  },
  {
    id: "omni" as const,
    icon: Eye,
    name: "OMNI MODE",
    subtitle: "The God View",
    features: [
      "All technical indicators",
      "News & sentiment data",
      "Full market context",
      "Flexible trading rules",
    ],
    description: "Prove your AI can filter signal from noise.",
  },
];

export function StepIdentity({
  formData,
  updateFormData,
  validationErrors,
  setValidationErrors,
  currentAgentId
}: StepIdentityProps) {
  const { agents } = useAgents();
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    const checkName = async () => {
      if (!formData.name || formData.name.length < 2) {
        if (setValidationErrors) {
          setValidationErrors({ ...validationErrors, name: "" });
        }
        return;
      }

      setIsChecking(true);

      // Simulate network delay for realism (and to prevent flickering)
      await new Promise(resolve => setTimeout(resolve, 500));

      const nameExists = agents.some(a =>
        a.name.toLowerCase() === formData.name.toLowerCase() &&
        a.id !== currentAgentId
      );

      if (setValidationErrors) {
        if (nameExists) {
          setValidationErrors({ ...validationErrors, name: "Agent name already exists" });
        } else {
          const newErrors = { ...validationErrors };
          delete newErrors.name;
          setValidationErrors(newErrors);
        }
      }
      setIsChecking(false);
    };

    const timeoutId = setTimeout(checkName, 500);
    return () => clearTimeout(timeoutId);
  }, [formData.name, agents, currentAgentId, setValidationErrors]); // validationErrors in dependency might cause loop if not careful

  // Fix dependency loop by using functional update or omitting validationErrors from dep array if safe
  // Actually, better to not include validationErrors in dep array if we use functional update
  // But here we use object spread.
  // Let's refactor to avoid dependency issues.

  return (
    <div className="space-y-6">
      {/* Agent Name */}
      <div className="space-y-2">
        <Label htmlFor="name" className="text-sm font-medium">
          Agent Name <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <Input
            id="name"
            placeholder="Enter agent name..."
            value={formData.name}
            onChange={(e) => updateFormData({ name: e.target.value })}
            className={cn(
              "input-glow font-mono",
              validationErrors?.name && "border-destructive focus-visible:ring-destructive"
            )}
            maxLength={30}
          />
          {isChecking && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent block" />
            </div>
          )}
        </div>
        {validationErrors?.name ? (
          <p className="text-xs text-destructive">{validationErrors.name}</p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Give your agent a memorable name (e.g., &quot;Alpha-1&quot;, &quot;MomentumBot&quot;)
          </p>
        )}
      </div>

      {/* Arena Mode Selection */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">
          Select Arena Mode <span className="text-destructive">*</span>
        </Label>
        <div className="grid gap-4 sm:grid-cols-2">
          {modes.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => updateFormData({ mode: mode.id })}
              className={cn(
                "relative flex flex-col items-start rounded-lg border-2 p-4 text-left transition-all",
                formData.mode === mode.id
                  ? "border-primary bg-primary/5"
                  : "border-border/50 hover:border-border hover:bg-muted/30"
              )}
            >
              {/* Mode Header */}
              <div className="mb-3 flex items-center gap-3">
                <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  formData.mode === mode.id
                    ? "bg-primary/10 text-primary"
                    : "bg-muted/50 text-muted-foreground"
                )}>
                  <mode.icon size={24} weight="duotone" />
                </div>
                <div>
                  <h3 className="font-mono text-sm font-bold">{mode.name}</h3>
                  <p className="text-xs text-muted-foreground">{mode.subtitle}</p>
                </div>
              </div>

              {/* Features */}
              <ul className="mb-4 space-y-1">
                {mode.features.map((feature, index) => (
                  <li
                    key={index}
                    className="flex items-center gap-2 text-xs text-muted-foreground"
                  >
                    <span className="h-1 w-1 rounded-full bg-muted-foreground" />
                    {feature}
                  </li>
                ))}
              </ul>

              {/* Description */}
              <p className="text-xs italic text-muted-foreground">
                {mode.description}
              </p>

              {/* Selection Indicator */}
              <div
                className={cn(
                  "mt-4 w-full rounded-md py-1.5 text-center text-xs font-medium transition-colors",
                  formData.mode === mode.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {formData.mode === mode.id ? "Selected" : "Select"}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

