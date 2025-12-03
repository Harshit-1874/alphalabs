"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, Bot, History, Play } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAgentsStore } from "@/lib/stores";
import type { QuickTestModalProps } from "@/types/dashboard";

export function QuickTestModal({ open, onOpenChange }: QuickTestModalProps) {
  const router = useRouter();
  const { agents } = useAgentsStore();
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [testType, setTestType] = useState<"backtest" | "forward">("backtest");

  const agent = agents.find((a) => a.id === selectedAgent);
  const canForwardTest = agent && (agent.stats.profitableTests ?? 0) > 0;

  const handleStartTest = () => {
    if (!selectedAgent) return;
    
    const path = testType === "backtest" 
      ? `/dashboard/arena/backtest?agent=${selectedAgent}`
      : `/dashboard/arena/forward?agent=${selectedAgent}`;
    
    router.push(path);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] overflow-hidden p-0 gap-0">
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ 
            type: "spring", 
            stiffness: 350, 
            damping: 30,
            mass: 0.8
          }}
          className="p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Quick Test
          </DialogTitle>
          <DialogDescription>
            Jump straight into testing. Select an agent and test type.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Agent Selection */}
          <div className="space-y-2">
            <Label>Select Agent</Label>
            <AnimatedSelect value={selectedAgent} onValueChange={setSelectedAgent}>
              <AnimatedSelectTrigger>
                <AnimatedSelectValue placeholder="Choose an agent..." />
              </AnimatedSelectTrigger>
              <AnimatedSelectContent>
                {agents.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No agents yet. Create one first!
                  </div>
                ) : (
                  agents.map((agent) => (
                    <AnimatedSelectItem key={agent.id} value={agent.id} textValue={agent.name}>
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        <span className="font-mono">{agent.name}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {agent.mode}
                        </Badge>
                      </div>
                    </AnimatedSelectItem>
                  ))
                )}
              </AnimatedSelectContent>
            </AnimatedSelect>
          </div>

          {/* Test Type Selection */}
          <div className="space-y-2">
            <Label>Test Type</Label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setTestType("backtest")}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all",
                  testType === "backtest"
                    ? "border-primary bg-primary/5"
                    : "border-border/50 hover:border-border"
                )}
              >
                <History className="h-6 w-6" />
                <span className="text-sm font-medium">Backtest</span>
                <span className="text-xs text-muted-foreground">Historical data</span>
              </button>
              <button
                type="button"
                onClick={() => setTestType("forward")}
                disabled={!canForwardTest && selectedAgent !== ""}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all",
                  testType === "forward"
                    ? "border-[hsl(var(--accent-profit))] bg-[hsl(var(--accent-profit)/0.05)]"
                    : "border-border/50 hover:border-border",
                  !canForwardTest && selectedAgent && "opacity-50 cursor-not-allowed"
                )}
              >
                <Play className="h-6 w-6" />
                <span className="text-sm font-medium">Forward Test</span>
                <span className="text-xs text-muted-foreground">Live paper trading</span>
              </button>
            </div>
            {selectedAgent && !canForwardTest && (
              <p className="text-xs text-[hsl(var(--accent-amber))]">
                Forward testing requires at least one profitable backtest
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleStartTest}
            disabled={!selectedAgent}
            className={cn(
              testType === "backtest"
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-[hsl(var(--accent-profit))] text-black hover:bg-[hsl(var(--accent-profit))]/90"
            )}
          >
            <Zap className="mr-2 h-4 w-4" />
            Start {testType === "backtest" ? "Backtest" : "Forward Test"}
          </Button>
        </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}

