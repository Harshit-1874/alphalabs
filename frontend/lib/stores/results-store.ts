/**
 * Results Store - Test results, filters
 */

import { create } from "zustand";
import type { TestResult, ResultFilters, ResultsStats } from "@/types";
import { DUMMY_RESULTS, DUMMY_RESULTS_STATS } from "@/lib/dummy-data";

interface ResultsState {
  // Data
  results: TestResult[];
  stats: ResultsStats;
  selectedResultId: string | null;
  
  // Filters
  filters: ResultFilters;
  setSearchQuery: (query: string) => void;
  setTypeFilter: (type: ResultFilters["type"]) => void;
  setResultFilter: (result: ResultFilters["result"]) => void;
  setAgentFilter: (agentId: string | undefined) => void;
  clearFilters: () => void;
  
  // Selection
  selectResult: (id: string | null) => void;
  
  // Refresh trigger - increment to trigger refresh
  refreshKey: number;
  triggerRefresh: () => void;
  
  // Computed
  filteredResults: () => TestResult[];
  
  // Pagination
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  totalPages: () => number;
  paginatedResults: () => TestResult[];
}

const defaultFilters: ResultFilters = {
  search: "",
  type: "all",
  result: "all",
  agentId: undefined,
};

export const useResultsStore = create<ResultsState>((set, get) => ({
  // Data - using dummy data
  results: DUMMY_RESULTS,
  stats: DUMMY_RESULTS_STATS,
  selectedResultId: null,

  // Refresh trigger
  refreshKey: 0,
  triggerRefresh: () => set((state) => ({ refreshKey: state.refreshKey + 1 })),

  // Filters
  filters: defaultFilters,
  setSearchQuery: (query) =>
    set((state) => ({ filters: { ...state.filters, search: query }, page: 1 })),
  setTypeFilter: (type) =>
    set((state) => ({ filters: { ...state.filters, type }, page: 1 })),
  setResultFilter: (result) =>
    set((state) => ({ filters: { ...state.filters, result }, page: 1 })),
  setAgentFilter: (agentId) =>
    set((state) => ({ filters: { ...state.filters, agentId }, page: 1 })),
  clearFilters: () => set({ filters: defaultFilters, page: 1 }),

  // Selection
  selectResult: (id) => set({ selectedResultId: id }),

  // Computed - returns filtered results
  filteredResults: () => {
    const { results, filters } = get();
    let filtered = [...results];

    // Search filter
    if (filters.search) {
      const query = filters.search.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.agentName.toLowerCase().includes(query) ||
          r.asset.toLowerCase().includes(query)
      );
    }

    // Type filter
    if (filters.type !== "all") {
      filtered = filtered.filter((r) => r.type === filters.type);
    }

    // Result filter
    if (filters.result === "profitable") {
      filtered = filtered.filter((r) => r.pnl >= 0);
    } else if (filters.result === "loss") {
      filtered = filtered.filter((r) => r.pnl < 0);
    }

    // Agent filter
    if (filters.agentId) {
      filtered = filtered.filter((r) => r.agentId === filters.agentId);
    }

    // Sort by date (newest first)
    filtered.sort((a, b) => b.date.getTime() - a.date.getTime());

    return filtered;
  },

  // Pagination
  page: 1,
  pageSize: 10,
  setPage: (page) => set({ page }),
  totalPages: () => {
    const filtered = get().filteredResults();
    return Math.ceil(filtered.length / get().pageSize);
  },
  paginatedResults: () => {
    const { page, pageSize, filteredResults } = get();
    const filtered = filteredResults();
    const start = (page - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  },
}));

