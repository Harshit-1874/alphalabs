"use client"

import { useEffect, useRef } from "react"
import {
  useDynamicIslandStore,
  type LiveSessionData,
  type NarratorData,
  type TradeData,
} from "@/lib/stores/dynamic-island-store"
import {
  DUMMY_ACTIVITY,
  DUMMY_DASHBOARD_STATS,
  DUMMY_LIVE_SESSIONS,
  DUMMY_RESULTS,
  DUMMY_RESULTS_STATS,
  DUMMY_TRADES,
} from "@/lib/dummy-data"

type RotationContext = "dashboard"
type RotationStep = {
  duration: number
  run: () => void
}

export interface PreparingConfig {
  type: "backtest" | "forward";
}

const buildDashboardSequence = (): RotationStep[] => {
  const store = useDynamicIslandStore.getState()

  const narratorData: NarratorData = {
    text: "Your LLM collective is compounding edge",
    type: "info",
    details: `Agents live: ${DUMMY_DASHBOARD_STATS.totalAgents} • Avg PnL: +${DUMMY_RESULTS_STATS.avgPnL}%`,
    metrics: [
      { label: "Win rate", value: `${DUMMY_RESULTS_STATS.profitablePercent}%` },
      { label: "Tests run", value: `${DUMMY_DASHBOARD_STATS.testsRun}` },
      { label: "Best agent", value: DUMMY_DASHBOARD_STATS.bestAgent },
    ],
  }

  const liveSessionData: LiveSessionData =
    DUMMY_LIVE_SESSIONS[0] || {
      id: "session-demo",
      agentId: "agent-demo",
      agentName: "α-demo",
      asset: "BTC/USDT",
      startedAt: new Date(),
      duration: "3h 04m",
      pnl: 1.8,
      trades: 4,
      winRate: 75,
      status: "running",
    }

  const narratorAction = () => store.narrate(narratorData.text, narratorData.type, narratorData)
  const liveSessionAction = () => store.showLiveSession(liveSessionData)
  const idleAction = () => store.showIdle()

  const activity = DUMMY_ACTIVITY?.[0]
  const secondNarratorAction =
    activity &&
    (() => {
      const text = `Agent ${activity.agentName} wrapped ${activity.description.toLowerCase()}`
      
      // Find matching result data for metrics
      const result = activity.resultId 
        ? DUMMY_RESULTS.find(r => r.id === activity.resultId)
        : null
      
      const narratorData: NarratorData = {
        text,
        type: activity.pnl && activity.pnl > 0 ? "result" : "info",
          details: `PnL ${activity.pnl?.toFixed(1) ?? "0"}% | Result ${activity.resultId ?? "–"}`,
        metrics: result ? [
          { label: "PnL", value: `${result.pnl.toFixed(1)}%` },
          { label: "Trades", value: `${result.trades}` },
          { label: "Win rate", value: `${result.winRate}%` },
        ] : activity.pnl ? [
          { label: "PnL", value: `${activity.pnl.toFixed(1)}%` },
        ] : undefined,
      }
      
      return store.narrate(narratorData.text, narratorData.type, narratorData)
    })

  const sequence: RotationStep[] = [
    // Idle mode shows formula quotes in the UI
    { duration: 8000, run: idleAction },
    // User info / performance pulse via narrator view
    { duration: 9000, run: narratorAction },
    // Live trading presence
    { duration: 10000, run: liveSessionAction },
  ]

  if (secondNarratorAction) {
    sequence.push({ duration: 7000, run: secondNarratorAction })
  }

  return sequence
}

const buildSequence = (context: RotationContext): RotationStep[] => {
  switch (context) {
    case "dashboard":
      return buildDashboardSequence()
    default:
      return []
  }
}

export const useDynamicIslandDemoRotation = (
  context: RotationContext | null,
  preparingConfig?: PreparingConfig
) => {
  const timeoutRef = useRef<number | null>(null)
  const stepIndexRef = useRef(0)

  useEffect(() => {
    const store = useDynamicIslandStore.getState()

    // If preparing config is provided, show the preparing animation
    if (preparingConfig) {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      store.showPreparing({ type: preparingConfig.type })
      return
    }

    // If no context, show idle (for battle screens where battle-screen.tsx controls)
    if (!context) {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      // Don't call showIdle - let battle-screen.tsx take control
      return
    }

    // Otherwise run the rotation sequence (dashboard)
    const steps = buildSequence(context)

    if (!steps.length) {
      return
    }

    const runStep = () => {
      const currentStep = steps[stepIndexRef.current % steps.length]
      currentStep.run()

      timeoutRef.current = window.setTimeout(() => {
        stepIndexRef.current = (stepIndexRef.current + 1) % steps.length
        runStep()
      }, currentStep.duration)
    }

    runStep()

    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      stepIndexRef.current = 0
    }
  }, [context, preparingConfig?.type])
}
