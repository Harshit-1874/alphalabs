"use client";

import { useEffect, useRef, memo, useCallback } from "react";
import { useTheme } from "next-themes";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
  type SeriesMarker,
} from "lightweight-charts";
import type { CandleData, TradeMarker } from "@/types";

interface CandlestickChartProps {
  data: CandleData[];
  markers?: TradeMarker[];
  height?: number;
  showVolume?: boolean;
  onCrosshairMove?: (price: number | null, time: number | null) => void;
}

// Helper to get computed CSS variable color values
function getCSSColor(variable: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const computed = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  if (!computed) return fallback;
  // CSS vars are stored as HSL values like "240 10% 4%", need to wrap in hsl()
  return `hsl(${computed})`;
}

// Theme-aware color configuration
function getChartColors(isDark: boolean) {
  return {
    // Use WHITE for dark mode axis labels, dark gray for light mode
    textColor: isDark ? "#e4e4e7" : "#3f3f46", // zinc-200 for dark, zinc-700 for light
    gridColor: isDark ? "rgba(63, 63, 70, 0.4)" : "rgba(228, 228, 231, 0.6)", // zinc-700/zinc-200
    borderColor: isDark ? "rgba(82, 82, 91, 0.6)" : "rgba(212, 212, 216, 0.8)", // zinc-600/zinc-300
    crosshairColor: "#10b981", // primary emerald
    crosshairLabelBg: "#00d4ff",
    upColor: isDark ? "#22c55e" : "#16a34a", // accent-green
    downColor: "#ef4444", // accent-red
    volumeColor: "rgba(16, 185, 129, 0.3)", // primary emerald with opacity
  };
}

function CandlestickChartComponent({
  data,
  markers = [],
  height = 400,
  showVolume = true,
  onCrosshairMove,
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const { resolvedTheme } = useTheme();
  
  const isDark = resolvedTheme === "dark" || resolvedTheme === undefined;

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const colors = getChartColors(isDark);

    // Create chart with theme-aware colors
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: colors.textColor,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: `${colors.crosshairColor}80`, // with alpha
          width: 1,
          style: 2,
          labelBackgroundColor: colors.crosshairLabelBg,
        },
        horzLine: {
          color: `${colors.crosshairColor}80`,
          width: 1,
          style: 2,
          labelBackgroundColor: colors.crosshairLabelBg,
        },
      },
      rightPriceScale: {
        borderColor: colors.borderColor,
        scaleMargins: {
          top: 0.1,
          bottom: showVolume ? 0.25 : 0.1,
        },
      },
      timeScale: {
        borderColor: colors.borderColor,
        timeVisible: true,
        secondsVisible: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
      },
      handleScroll: {
        vertTouchDrag: false,
      },
    });

    // Candlestick series - v5 API with theme-aware colors
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.upColor,
      downColor: colors.downColor,
      borderUpColor: colors.upColor,
      borderDownColor: colors.downColor,
      wickUpColor: colors.upColor,
      wickDownColor: colors.downColor,
    });

    // Volume series (if enabled) - v5 API
    let volumeSeries: ISeriesApi<"Histogram"> | null = null;
    if (showVolume) {
      volumeSeries = chart.addSeries(HistogramSeries, {
        color: colors.volumeColor,
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.85,
          bottom: 0,
        },
      });
    }

    // Store refs
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    // Crosshair move handler
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove((param) => {
        if (!param.time || !param.point) {
          onCrosshairMove(null, null);
          return;
        }
        const price = param.seriesData.get(candleSeries);
        if (price && "close" in price) {
          onCrosshairMove(price.close, param.time as number);
        }
      });
    }

    // Resize handler
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [showVolume, onCrosshairMove, isDark]);

  // Track previous data length and last candle for incremental updates
  const prevDataLengthRef = useRef(0);
  const prevLastCandleRef = useRef<CandleData | null>(null);

  // Update data
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    
    if (data.length === 0) {
      // Clear chart if no data - but don't remove the chart itself
      // This allows the chart to remain visible with empty state
      try {
        candleSeriesRef.current.setData([]);
        if (volumeSeriesRef.current) {
          volumeSeriesRef.current.setData([]);
        }
      } catch (error) {
        // Ignore errors when clearing empty data
        console.debug("Chart clear error (expected when empty):", error);
      }
      return;
    }

    const colors = getChartColors(isDark);
    const sortedData = [...data].sort((a, b) => a.time - b.time);
    const currentLength = sortedData.length;
    const prevLength = prevDataLengthRef.current;

    // For real-time updates: if only the last candle changed, use update() for better performance
    // Otherwise, use setData() for full replacement
    if (prevLength > 0 && currentLength === prevLength) {
      // Only last candle updated - use incremental update
      const lastCandle = sortedData[sortedData.length - 1];
      const prevLastCandle = prevLastCandleRef.current;
      
      // Check if the new last candle is actually newer or equal to the previous one
      // This prevents errors when fast-forwarding sends older candles
      const canUpdate = !prevLastCandle || lastCandle.time >= prevLastCandle.time;
      
      if (canUpdate) {
        const lastCandleData: CandlestickData<Time> = {
          time: (lastCandle.time / 1000) as Time,
          open: lastCandle.open,
          high: lastCandle.high,
          low: lastCandle.low,
          close: lastCandle.close,
        };
        
        // Only update if the time is >= the last candle's time
        // Lightweight Charts requires this for update() to work
        try {
          candleSeriesRef.current.update(lastCandleData);

          // Update volume if enabled
          if (volumeSeriesRef.current && showVolume) {
            const lastVolumeData = {
              time: (lastCandle.time / 1000) as Time,
              value: lastCandle.volume,
              color:
                lastCandle.close >= lastCandle.open
                  ? `${colors.upColor}66`
                  : `${colors.downColor}66`,
            };
            volumeSeriesRef.current.update(lastVolumeData);
          }
        } catch (error) {
          // If update fails (e.g., time is older), fall back to setData
          console.warn("Failed to update candle, using setData instead:", error);
          const candleData: CandlestickData<Time>[] = sortedData.map((d) => ({
            time: (d.time / 1000) as Time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          }));
          candleSeriesRef.current.setData(candleData);
          
          if (volumeSeriesRef.current && showVolume) {
            const volumeData = sortedData.map((d) => ({
              time: (d.time / 1000) as Time,
              value: d.volume,
              color:
                d.close >= d.open
                  ? `${colors.upColor}66`
                  : `${colors.downColor}66`,
            }));
            volumeSeriesRef.current.setData(volumeData);
          }
        }
      } else {
        // New candle is older than previous - use setData to replace all
        const candleData: CandlestickData<Time>[] = sortedData.map((d) => ({
          time: (d.time / 1000) as Time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));
        candleSeriesRef.current.setData(candleData);
        
        if (volumeSeriesRef.current && showVolume) {
          const volumeData = sortedData.map((d) => ({
            time: (d.time / 1000) as Time,
            value: d.volume,
            color:
              d.close >= d.open
                ? `${colors.upColor}66`
                : `${colors.downColor}66`,
          }));
          volumeSeriesRef.current.setData(volumeData);
        }
      }
      
      // Update the ref to track current length and last candle
      prevDataLengthRef.current = currentLength;
      if (sortedData.length > 0) {
        prevLastCandleRef.current = sortedData[sortedData.length - 1];
      }
    } else {
      // New candle added or full data replacement - use setData()
      const candleData: CandlestickData<Time>[] = sortedData.map((d) => ({
        time: (d.time / 1000) as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }));

      candleSeriesRef.current.setData(candleData);

      // Volume data with theme-aware colors
      if (volumeSeriesRef.current && showVolume) {
        const volumeData = sortedData.map((d) => ({
          time: (d.time / 1000) as Time,
          value: d.volume,
          color:
            d.close >= d.open
              ? `${colors.upColor}66`
              : `${colors.downColor}66`,
        }));
        volumeSeriesRef.current.setData(volumeData);
      }

      // Fit content only on full updates
      chartRef.current?.timeScale().fitContent();
      
      // Update refs for next comparison
      prevDataLengthRef.current = currentLength;
      if (sortedData.length > 0) {
        prevLastCandleRef.current = sortedData[sortedData.length - 1];
      }
    }
  }, [data, showVolume, isDark]);

  useEffect(() => {
    if (!candleSeriesRef.current) return;
    if (!markers || markers.length === 0) {
      (candleSeriesRef.current as unknown as { setMarkers?: (markers: SeriesMarker<Time>[]) => void }).setMarkers?.([]);
      return;
    }

    const markerStyles: Record<string, { color: string; shape: "arrowUp" | "arrowDown" | "circle"; text: string }> = {
      "entry-long": { color: "#22c55e", shape: "arrowUp", text: "L" },
      "entry-short": { color: "#ef4444", shape: "arrowDown", text: "S" },
      "exit-profit": { color: "#10b981", shape: "circle", text: "TP" },
      "exit-loss": { color: "#f87171", shape: "circle", text: "SL" },
    };

    const chartMarkers: SeriesMarker<Time>[] = [...markers]
      .sort((a, b) => a.time - b.time)
      .map((marker) => {
      const style = markerStyles[marker.type] ?? markerStyles["entry-long"];
      return {
        time: (marker.time / 1000) as Time,
        position: marker.position === "above" ? "aboveBar" : "belowBar",
        color: style.color,
        shape: style.shape,
        text: marker.label ?? style.text,
        size: 1,
        ...(marker.price ? { price: marker.price } : {}),
      };
      });

    const series = candleSeriesRef.current as unknown as { setMarkers?: (markers: SeriesMarker<Time>[]) => void };
    series.setMarkers?.(chartMarkers);
  }, [markers]);

  return (
    <div
      ref={chartContainerRef}
      style={{ height }}
      className="w-full rounded-lg bg-card/30"
    />
  );
}

export const CandlestickChart = memo(CandlestickChartComponent);
