"use client";

import { LayoutGrid, List, Bot, Plus, Loader2 } from "lucide-react";
import Link from "next/link";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Button } from "@/components/ui/button";
import { AgentCard } from "./agent-card";
import { CreateAgentCard } from "./create-agent-card";
import { useAgents } from "@/hooks/use-agents";
import { useState } from "react";

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-6 rounded-full bg-muted/50 p-6">
        <Bot className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="font-mono text-xl font-semibold">No agents yet</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Create your first AI agent to start testing trading strategies in The Arena
      </p>
      <Button asChild className="mt-6 gap-2">
        <Link href="/dashboard/agents/new">
          <Plus className="h-4 w-4" />
          Create Your First Agent
        </Link>
      </Button>
    </div>
  );
}

function NoResultsState({ onClear }: { onClear: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-6 rounded-full bg-muted/50 p-6">
        <Bot className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="font-mono text-xl font-semibold">No matching agents</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Try adjusting your search or filters
      </p>
      <Button variant="outline" className="mt-4" onClick={onClear}>
        Clear Filters
      </Button>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      <p className="mt-4 text-sm text-muted-foreground">Loading agents...</p>
    </div>
  );
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-6 rounded-full bg-destructive/10 p-6">
        <Bot className="h-12 w-12 text-destructive" />
      </div>
      <h3 className="font-mono text-xl font-semibold">Failed to load agents</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{error}</p>
      <Button variant="outline" className="mt-4" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

export function AgentsView() {
  const [view, setView] = useState<"grid" | "list">("grid");
  const { agents, total, isLoading, error, filters, updateFilters, refetch } = useAgents();

  const hasFilters = !!(filters.search || filters.mode || filters.model);

  // Loading state
  if (isLoading) {
    return <LoadingState />;
  }

  // Error state
  if (error) {
    return <ErrorState error={error} onRetry={refetch} />;
  }

  // Empty state (no agents at all)
  if (!isLoading && agents.length === 0 && !hasFilters) {
    return <EmptyState />;
  }

  // No results with filters
  if (agents.length === 0 && hasFilters) {
    return <NoResultsState onClear={() => updateFilters({ search: undefined, mode: undefined, model: undefined })} />;
  }

  return (
    <div className="space-y-4">
      {/* View Toggle */}
      <div className="flex items-center justify-between">
        <ToggleGroup
          type="single"
          value={view}
          onValueChange={(value) => value && setView(value as "grid" | "list")}
          className="gap-1"
        >
          <ToggleGroupItem
            value="grid"
            aria-label="Grid view"
            className="data-[state=on]:bg-muted"
          >
            <LayoutGrid className="h-4 w-4" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="list"
            aria-label="List view"
            className="data-[state=on]:bg-muted"
          >
            <List className="h-4 w-4" />
          </ToggleGroupItem>
        </ToggleGroup>

        <span className="text-xs text-muted-foreground">
          Showing {agents.length} of {total} agent{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Grid View */}
      {view === "grid" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
          <CreateAgentCard />
        </div>
      )}

      {/* List View */}
      {view === "list" && (
        <div className="space-y-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} variant="list" />
          ))}
        </div>
      )}
    </div>
  );
}
