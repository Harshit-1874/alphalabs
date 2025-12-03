"use client";

import { Search, Filter, ArrowUpDown, Plus, X } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AnimatedDropdown,
  AnimatedDropdownContent,
  AnimatedDropdownCheckboxItem,
  AnimatedDropdownLabel,
  AnimatedDropdownSeparator,
  AnimatedDropdownTrigger,
} from "@/components/ui/animated-dropdown";
import { Badge } from "@/components/ui/badge";
import { useAgentsStore } from "@/lib/stores";
import type { AgentMode } from "@/types";

export function AgentsPageHeader() {
  const {
    agents,
    filters,
    setSearchQuery,
    toggleModelFilter,
    toggleModeFilter,
    setSortBy,
    clearFilters,
  } = useAgentsStore();

  const activeFiltersCount = filters.models.length + filters.modes.length;

  return (
    <div className="space-y-4">
      {/* Title Row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold tracking-tight md:text-3xl">
            My Agents
          </h1>
          <p className="text-sm text-muted-foreground">
            {agents.length} agent{agents.length !== 1 ? "s" : ""} configured
          </p>
        </div>

        {/* Primary CTA */}
        <Button
          asChild
          className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Link href="/dashboard/agents/new">
            <Plus className="h-4 w-4" />
            New Agent
          </Link>
        </Button>
      </div>

      {/* Actions Row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={filters.search}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-9 input-glow"
          />
          {filters.search && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2"
              onClick={() => setSearchQuery("")}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        {/* Filter Dropdown */}
        <AnimatedDropdown>
          <AnimatedDropdownTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <Filter className="h-4 w-4" />
              Filter
              {activeFiltersCount > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 w-5 rounded-full p-0 text-xs"
                >
                  {activeFiltersCount}
                </Badge>
              )}
            </Button>
          </AnimatedDropdownTrigger>
          <AnimatedDropdownContent align="start" className="w-56">
            <AnimatedDropdownLabel>Model</AnimatedDropdownLabel>
            <AnimatedDropdownCheckboxItem
              checked={filters.models.includes("deepseek-r1")}
              onCheckedChange={() => toggleModelFilter("deepseek-r1")}
            >
              DeepSeek-R1
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.models.includes("claude-3.5")}
              onCheckedChange={() => toggleModelFilter("claude-3.5")}
            >
              Claude 3.5
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.models.includes("gemini-1.5")}
              onCheckedChange={() => toggleModelFilter("gemini-1.5")}
            >
              Gemini 1.5 Pro
            </AnimatedDropdownCheckboxItem>

            <AnimatedDropdownSeparator />

            <AnimatedDropdownLabel>Mode</AnimatedDropdownLabel>
            <AnimatedDropdownCheckboxItem
              checked={filters.modes.includes("monk")}
              onCheckedChange={() => toggleModeFilter("monk" as AgentMode)}
            >
              Monk Mode
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.modes.includes("omni")}
              onCheckedChange={() => toggleModeFilter("omni" as AgentMode)}
            >
              Omni Mode
            </AnimatedDropdownCheckboxItem>

            {activeFiltersCount > 0 && (
              <>
                <AnimatedDropdownSeparator />
                <div className="p-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full"
                    onClick={clearFilters}
                  >
                    Clear All
                  </Button>
                </div>
              </>
            )}
          </AnimatedDropdownContent>
        </AnimatedDropdown>

        {/* Sort Dropdown */}
        <AnimatedDropdown>
          <AnimatedDropdownTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <ArrowUpDown className="h-4 w-4" />
              Sort
            </Button>
          </AnimatedDropdownTrigger>
          <AnimatedDropdownContent align="start">
            <AnimatedDropdownCheckboxItem
              checked={filters.sortBy === "newest"}
              onCheckedChange={() => setSortBy("newest")}
            >
              Newest First
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.sortBy === "oldest"}
              onCheckedChange={() => setSortBy("oldest")}
            >
              Oldest First
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.sortBy === "performance"}
              onCheckedChange={() => setSortBy("performance")}
            >
              Best Performance
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.sortBy === "tests"}
              onCheckedChange={() => setSortBy("tests")}
            >
              Most Tests
            </AnimatedDropdownCheckboxItem>
            <AnimatedDropdownCheckboxItem
              checked={filters.sortBy === "alpha"}
              onCheckedChange={() => setSortBy("alpha")}
            >
              Alphabetical
            </AnimatedDropdownCheckboxItem>
          </AnimatedDropdownContent>
        </AnimatedDropdown>
      </div>
    </div>
  );
}
