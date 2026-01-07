/**
 * Active Sessions Provider
 * Polls the combined /api/arena/active endpoint and updates the sessions store
 * This ensures only ONE API call is made for all active sessions across the app
 */

"use client";

import { useEffect, useRef, useCallback } from "react";
import { useApiClient } from "@/lib/api";
import { useSessionsStore } from "@/lib/stores/sessions-store";
import type { ForwardSession } from "@/hooks/use-forward-sessions";

interface ActiveSessionsResponse {
  forward: Array<{
    id: string;
    agent_id: string;
    agent_name: string;
    asset: string;
    status: "running" | "paused" | "initializing";
    started_at: string;
    duration_display: string;
    current_pnl_pct: number;
    trades_count: number;
    win_rate: number;
  }>;
  backtest: Array<{
    id: string;
    agent_id: string;
    agent_name: string;
    asset: string;
    status: "running" | "paused" | "initializing";
    started_at: string;
    duration_display: string;
    current_pnl_pct: number;
    trades_count: number;
    win_rate: number;
  }>;
}

const mapSession = (session: ActiveSessionsResponse["forward"][number]): ForwardSession => ({
  id: session.id,
  agentId: session.agent_id,
  agentName: session.agent_name,
  asset: session.asset,
  status: session.status,
  startedAt: session.started_at,
  durationDisplay: session.duration_display,
  currentPnlPct: session.current_pnl_pct,
  tradesCount: session.trades_count,
  winRate: session.win_rate,
});

// Deep equality check for sessions array
function sessionsEqual(a: ForwardSession[], b: ForwardSession[]): boolean {
  if (a.length !== b.length) return false;
  
  const aMap = new Map(a.map(s => [s.id, s]));
  const bMap = new Map(b.map(s => [s.id, s]));
  
  for (const session of a) {
    const other = bMap.get(session.id);
    if (!other) return false;
    
    if (
      session.agentId !== other.agentId ||
      session.agentName !== other.agentName ||
      session.asset !== other.asset ||
      session.status !== other.status ||
      session.startedAt !== other.startedAt ||
      session.durationDisplay !== other.durationDisplay ||
      Math.abs(session.currentPnlPct - other.currentPnlPct) > 0.0001 ||
      session.tradesCount !== other.tradesCount ||
      Math.abs(session.winRate - other.winRate) > 0.0001
    ) {
      return false;
    }
  }
  
  for (const session of b) {
    if (!aMap.has(session.id)) return false;
  }
  
  return true;
}

// Global request deduplication cache
const requestCache = new Map<string, { promise: Promise<ActiveSessionsResponse>; timestamp: number }>();
const CACHE_TTL = 2000; // 2 seconds cache to prevent duplicate simultaneous requests

interface ActiveSessionsProviderProps {
  pollInterval?: number;
  children: React.ReactNode;
}

export function ActiveSessionsProvider({ 
  pollInterval = 15000, 
  children 
}: ActiveSessionsProviderProps) {
  const { get } = useApiClient();
  const {
    setForwardSessions,
    setBacktestSessions,
    setLoading,
    setError,
    setLastFetchedAt,
    forwardSessions: currentForwardSessions,
    backtestSessions: currentBacktestSessions,
  } = useSessionsStore();
  
  const isMountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const previousForwardRef = useRef<ForwardSession[]>([]);
  const previousBacktestRef = useRef<ForwardSession[]>([]);

  const fetchSessions = useCallback(async () => {
    const cacheKey = "/api/arena/active";
    const now = Date.now();
    
    // Check cache for recent request
    const cached = requestCache.get(cacheKey);
    if (cached && (now - cached.timestamp) < CACHE_TTL) {
      try {
        const response = await cached.promise;
        if (isMountedRef.current) {
          const newForwardSessions = response.forward.map(mapSession);
          const newBacktestSessions = response.backtest.map(mapSession);
          
          // Only update if data actually changed
          if (!sessionsEqual(newForwardSessions, previousForwardRef.current)) {
            previousForwardRef.current = newForwardSessions;
            setForwardSessions(newForwardSessions);
          }
          if (!sessionsEqual(newBacktestSessions, previousBacktestRef.current)) {
            previousBacktestRef.current = newBacktestSessions;
            setBacktestSessions(newBacktestSessions);
          }
          setLastFetchedAt(now);
          setLoading(false);
        }
        return;
      } catch (err) {
        // Cache failed, continue with new request
        requestCache.delete(cacheKey);
      }
    }

    // Create new request and cache it
    setLoading(true);
    setError(null);
    
    const requestPromise = get<ActiveSessionsResponse>(cacheKey);
    requestCache.set(cacheKey, { promise: requestPromise, timestamp: now });
    
    // Clean up old cache entries
    for (const [key, value] of requestCache.entries()) {
      if (now - value.timestamp > CACHE_TTL) {
        requestCache.delete(key);
      }
    }

    try {
      const response = await requestPromise;
      if (isMountedRef.current) {
        const newForwardSessions = response.forward.map(mapSession);
        const newBacktestSessions = response.backtest.map(mapSession);
        
        // Only update if data actually changed
        if (!sessionsEqual(newForwardSessions, previousForwardRef.current)) {
          previousForwardRef.current = newForwardSessions;
          setForwardSessions(newForwardSessions);
        }
        if (!sessionsEqual(newBacktestSessions, previousBacktestRef.current)) {
          previousBacktestRef.current = newBacktestSessions;
          setBacktestSessions(newBacktestSessions);
        }
        setLastFetchedAt(now);
        setLoading(false);
      }
    } catch (err) {
      requestCache.delete(cacheKey);
      if (isMountedRef.current) {
        const message = err instanceof Error ? err.message : "Failed to load sessions";
        setError(message);
        setLoading(false);
      }
    }
  }, [get, setForwardSessions, setBacktestSessions, setLoading, setError, setLastFetchedAt]);

  useEffect(() => {
    isMountedRef.current = true;
    void fetchSessions();
    
    if (pollInterval > 0) {
      intervalRef.current = setInterval(() => {
        void fetchSessions();
      }, pollInterval);
    }
    
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchSessions, pollInterval]);

  return <>{children}</>;
}

