"use client";

import { History, Edit, MoreVertical, Copy, FileDown, Trash2, Bot } from "lucide-react";
import { Crosshair, Eye } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AnimatedDropdown,
  AnimatedDropdownContent,
  AnimatedDropdownItem,
  AnimatedDropdownSeparator,
  AnimatedDropdownTrigger,
} from "@/components/ui/animated-dropdown";
import { cn } from "@/lib/utils";
import { useAgents } from "@/hooks/use-agents";
import { toast } from "sonner";
import { useState } from "react";
import { DeleteAgentDialog } from "./delete-agent-dialog";
import { RotateCcw } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  model: string;
  mode: "monk" | "omni";
  indicators: string[];
  testsRun: number;
  bestPnL: number | null;
  createdAt: Date;
  isArchived?: boolean;
}

interface AgentCardProps {
  agent: Agent;
  variant?: "grid" | "list";
}

export function AgentCard({ agent, variant = "grid" }: AgentCardProps) {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/dashboard/agents/${agent.id}`);
  };

  const indicatorsPreview =
    agent.indicators.length > 3
      ? `${agent.indicators.slice(0, 3).join(", ")} +${agent.indicators.length - 3} more`
      : agent.indicators.join(", ");

  if (variant === "list") {
    return (
      <Card
        className={cn(
          "group cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-muted/30",
          agent.isArchived && "opacity-60"
        )}
        onClick={handleCardClick}
      >
        <CardContent className="flex items-center gap-4 p-4">
          {/* Icon */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted/50">
            <Bot className="h-5 w-5 text-muted-foreground" />
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold">{agent.name}</span>
              {agent.isArchived && (
                <Badge variant="secondary" className="text-[10px]">
                  Archived
                </Badge>
              )}
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] gap-1",
                  agent.mode === "monk"
                    ? "border-[hsl(var(--brand-lavender)/0.3)] text-[hsl(var(--brand-lavender))]"
                    : "border-primary/30 text-primary"
                )}
              >
                {agent.mode === "monk" ? (
                  <><Crosshair size={12} weight="duotone" /> Monk</>
                ) : (
                  <><Eye size={12} weight="duotone" /> Omni</>
                )}
              </Badge>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {agent.model} - {indicatorsPreview}
            </p>
          </div>

          {/* Stats */}
          <div className="hidden text-right sm:block">
            <p className="font-mono text-sm">{agent.testsRun} tests</p>
            {agent.bestPnL !== null ? (
              <p
                className={cn(
                  "font-mono text-xs",
                  agent.bestPnL >= 0
                    ? "text-[hsl(var(--accent-profit))]"
                    : "text-[hsl(var(--accent-red))]"
                )}
              >
                Best: {agent.bestPnL >= 0 ? "+" : ""}
                {agent.bestPnL}%
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">--</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => router.push(`/dashboard/arena/backtest?agent=${agent.id}`)}
              >
                <History className="h-4 w-4" />
              </Button>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => router.push(`/dashboard/agents/${agent.id}/edit`)}
              >
                <Edit className="h-4 w-4" />
              </Button>
            </motion.div>
            <AgentMoreMenu agentId={agent.id} agentName={agent.name} isArchived={agent.isArchived} />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className={cn(
        "group cursor-pointer border-border/50 bg-card/50 transition-all hover:border-border/80 hover:bg-muted/30",
        agent.isArchived && "opacity-60"
      )}
      onClick={handleCardClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50">
              <Bot className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono text-base font-semibold">{agent.name}</h3>
                {agent.isArchived && (
                  <Badge variant="secondary" className="text-[10px]">
                    Archived
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{agent.model}</p>
            </div>
          </div>
          <div onClick={(e) => e.stopPropagation()}>
            <AgentMoreMenu agentId={agent.id} agentName={agent.name} isArchived={agent.isArchived} />
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {/* Mode Section */}
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
          <Badge
            variant="outline"
            className={cn(
              "mb-2 gap-1.5",
              agent.mode === "monk"
                ? "border-[hsl(var(--brand-lavender)/0.3)] bg-[hsl(var(--brand-lavender)/0.1)] text-[hsl(var(--brand-lavender))]"
                : "border-primary/30 bg-primary/10 text-primary"
            )}
          >
            {agent.mode === "monk" ? (
              <><Crosshair size={14} weight="duotone" /> Monk Mode</>
            ) : (
              <><Eye size={14} weight="duotone" /> Omni Mode</>
            )}
          </Badge>
          <p className="text-xs text-muted-foreground">{indicatorsPreview}</p>
        </div>

        {/* Stats */}
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Tests: <span className="font-mono text-foreground">{agent.testsRun}</span>
          </span>
          <span className="text-muted-foreground">
            Best:{" "}
            {agent.bestPnL !== null ? (
              <span
                className={cn(
                  "font-mono",
                  agent.bestPnL >= 0
                    ? "text-[hsl(var(--accent-profit))]"
                    : "text-[hsl(var(--accent-red))]"
                )}
              >
                {agent.bestPnL >= 0 ? "+" : ""}
                {agent.bestPnL}%
              </span>
            ) : (
              <span className="font-mono text-foreground">--</span>
            )}
          </span>
        </div>
      </CardContent>

      <CardFooter
        className="gap-2 border-t border-border/50 pt-3"
        onClick={(e) => e.stopPropagation()}
      >
        <motion.div
          className="flex-1"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-1"
            onClick={() => router.push(`/dashboard/arena/backtest?agent=${agent.id}`)}
          >
            <History className="h-3 w-3" />
            Backtest
          </Button>
        </motion.div>
        <motion.div
          className="flex-1"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
          <Button
            variant="ghost"
            size="sm"
            className="w-full gap-1"
            onClick={() => router.push(`/dashboard/agents/${agent.id}/edit`)}
          >
            <Edit className="h-3 w-3" />
            Edit
          </Button>
        </motion.div>
      </CardFooter>
    </Card>
  );
}

function AgentMoreMenu({ agentId, agentName, isArchived }: { agentId: string; agentName: string; isArchived?: boolean }) {
  const { duplicateAgent, restoreAgent, deleteAgent } = useAgents();
  const [isDuplicating, setIsDuplicating] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDuplicate = async () => {
    if (isDuplicating) return;
    
    setIsDuplicating(true);
    try {
      const newName = `${agentName} (Copy)`;
      await duplicateAgent(agentId, newName);
      toast.success(`Agent "${newName}" created successfully!`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to duplicate agent";
      toast.error(errorMessage);
    } finally {
      setIsDuplicating(false);
    }
  };

  const handleRestore = async () => {
    if (isRestoring) return;
    
    setIsRestoring(true);
    try {
      await restoreAgent(agentId);
      toast.success(`Agent "${agentName}" restored successfully!`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to restore agent";
      toast.error(errorMessage);
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <>
      <AnimatedDropdown>
        <AnimatedDropdownTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </AnimatedDropdownTrigger>
      <AnimatedDropdownContent align="end">
        {isArchived ? (
          <>
            <AnimatedDropdownItem 
              onSelect={handleRestore}
              disabled={isRestoring}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              {isRestoring ? "Restoring..." : "Restore Agent"}
            </AnimatedDropdownItem>
            <AnimatedDropdownSeparator />
            <AnimatedDropdownItem destructive onSelect={() => setShowDeleteDialog(true)}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Permanently
            </AnimatedDropdownItem>
          </>
        ) : (
          <>
            <AnimatedDropdownItem 
              onSelect={handleDuplicate}
              disabled={isDuplicating}
            >
              <Copy className="mr-2 h-4 w-4" />
              {isDuplicating ? "Duplicating..." : "Duplicate Agent"}
            </AnimatedDropdownItem>
            <AnimatedDropdownItem onSelect={() => console.log("Export", agentId)}>
              <FileDown className="mr-2 h-4 w-4" />
              Export Config
            </AnimatedDropdownItem>
            <AnimatedDropdownSeparator />
            <AnimatedDropdownItem destructive onSelect={() => setShowDeleteDialog(true)}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Agent
            </AnimatedDropdownItem>
          </>
        )}
      </AnimatedDropdownContent>
      </AnimatedDropdown>
      <DeleteAgentDialog
        agentId={agentId}
        agentName={agentName}
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        isArchived={isArchived}
      />
    </>
  );
}

