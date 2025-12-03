"use client";

import { useState } from "react";
import { Check, Circle, X, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface Step {
  id: number;
  title: string;
  description: string;
  href: string;
  buttonLabel: string;
  status: "complete" | "current" | "upcoming";
}

// In a real app, this would come from user onboarding state
const initialSteps: Step[] = [
  {
    id: 1,
    title: "Create your first agent",
    description: "Configure an AI trading agent with your strategy",
    href: "/dashboard/agents/new",
    buttonLabel: "Create Agent",
    status: "current",
  },
  {
    id: 2,
    title: "Run a backtest",
    description: "Test your agent against historical data",
    href: "/dashboard/arena/backtest",
    buttonLabel: "Start Backtest",
    status: "upcoming",
  },
  {
    id: 3,
    title: "Generate your first certificate",
    description: "Get a verified proof of your AI's performance",
    href: "/dashboard/results",
    buttonLabel: "View Results",
    status: "upcoming",
  },
];

export function QuickStartGuide() {
  const [isDismissed, setIsDismissed] = useState(false);
  const [steps] = useState(initialSteps);

  // Calculate progress
  const completedSteps = steps.filter((s) => s.status === "complete").length;
  const progress = (completedSteps / steps.length) * 100;

  // Check if all steps are complete
  const isComplete = completedSteps === steps.length;

  // In real app, check user preference from localStorage or API
  if (isDismissed || isComplete) {
    return null;
  }

  // Get current step for CTA
  const currentStep = steps.find((s) => s.status === "current") || steps[0];

  return (
    <Card className="border-[hsl(var(--brand-flame)/0.3)] bg-gradient-to-br from-[hsl(var(--brand-flame)/0.05)] to-transparent">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="font-mono text-lg font-semibold">Quick Start Guide</CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-muted-foreground hover:text-foreground"
          onClick={() => setIsDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-mono text-foreground">
              {completedSteps}/{steps.length} complete
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Steps */}
        <div className="mb-6 space-y-4">
          {steps.map((step, index) => (
            <div key={step.id} className="relative flex items-start gap-4">
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "absolute left-[11px] top-8 h-[calc(100%+8px)] w-0.5",
                    step.status === "complete"
                      ? "bg-[hsl(var(--brand-flame))]"
                      : "bg-border"
                  )}
                />
              )}

              {/* Status Icon */}
              <div
                className={cn(
                  "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
                  step.status === "complete" &&
                    "border-[hsl(var(--brand-flame))] bg-[hsl(var(--brand-flame))]",
                  step.status === "current" &&
                    "border-primary bg-transparent",
                  step.status === "upcoming" && "border-border bg-transparent"
                )}
              >
                {step.status === "complete" ? (
                  <Check className="h-3 w-3 text-white" />
                ) : (
                  <Circle
                    className={cn(
                      "h-2 w-2",
                      step.status === "current"
                        ? "fill-primary text-primary"
                        : "fill-muted-foreground text-muted-foreground"
                    )}
                  />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-4">
                <h4
                  className={cn(
                    "text-sm font-medium",
                    step.status === "upcoming" && "text-muted-foreground"
                  )}
                >
                  {step.title}
                </h4>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Current Step CTA */}
        <Button asChild className="w-full gap-2">
          <Link href={currentStep.href}>
            {currentStep.buttonLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

