'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Line, ComposedChart } from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { historicalPrices, liveDeltaSequence, livePriceClamp, generateTimeLabels } from './carousel-data';

const chartConfig = {
  price: {
    label: 'BTC/USD',
    color: 'hsl(142, 76%, 36%)',
  },
  volume: {
    label: 'Volume',
    color: 'hsl(217, 91%, 60%)',
  },
} satisfies ChartConfig;

type LiveHeaderProps = {
  currentPrice: number;
  priceChange: number;
  percentChange: string;
  isCurrentGreen: boolean;
};

function LivePriceHeader({ currentPrice, priceChange, percentChange, isCurrentGreen }: LiveHeaderProps) {
  return (
    <div className="flex items-center justify-between px-4 pt-3 pb-2">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
          <span className="text-[10px] font-bold text-white">₿</span>
        </div>
        <div>
          <div className="text-[10px] text-white/50 uppercase tracking-wider">BTC/USD</div>
          <div className="text-sm font-semibold text-white font-mono">
            ${currentPrice.toLocaleString()}
          </div>
        </div>
      </div>

      <div className={`text-right ${isCurrentGreen ? 'text-emerald-400' : 'text-red-400'}`}>
        <div className="text-xs font-mono font-medium">
          {isCurrentGreen ? '↑' : '↓'} {priceChange >= 0 ? '+' : '-'}${Math.abs(priceChange).toFixed(0)}
        </div>
        <div className="text-[10px] font-mono">
          {priceChange >= 0 ? '+' : ''}{percentChange}%
        </div>
      </div>

      <LiveIndicator isCurrentGreen={isCurrentGreen} />
    </div>
  );
}

function LiveIndicator({ isCurrentGreen }: { isCurrentGreen: boolean }) {
  const color = isCurrentGreen ? 'bg-emerald-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-1.5">
      <div className="relative">
        <div className={`w-2 h-2 rounded-full ${color}`} />
        <div className={`absolute inset-0 w-2 h-2 rounded-full animate-ping opacity-75 ${color}`} />
      </div>
      <span className="text-[9px] text-white/40 uppercase tracking-wider">Live</span>
    </div>
  );
}

type ChartVisualizationProps = {
  chartData: Array<{ time: string; price: number }>;
  minPrice: number;
  maxPrice: number;
  gradientColor: string;
};

function ChartVisualization({ chartData, minPrice, maxPrice, gradientColor }: ChartVisualizationProps) {
  // Use the gradientColor prop which is already calculated based on current price change direction
  const lineColor = gradientColor;
  const gradientId = gradientColor === '#ef4444' ? 'redGradient' : 'greenGradient';

  return (
    <ChartContainer config={chartConfig} className="h-full w-full">
      <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
        <defs>
          {/* Green gradient */}
          <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
          </linearGradient>
          {/* Red gradient */}
          <linearGradient id="redGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="time"
          tickLine={false}
          axisLine={false}
          tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }}
          tickMargin={8}
          minTickGap={40}
        />
        <YAxis
          domain={[minPrice, maxPrice]}
          tickLine={false}
          axisLine={false}
          tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }}
          tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
          width={35}
        />
        <ChartTooltip
          cursor={{ stroke: 'rgba(255,255,255,0.1)' }}
          content={
            <ChartTooltipContent
              className="bg-white/5 backdrop-blur-md border border-white/20 rounded-lg px-3 py-2 shadow-xl"
              labelClassName="text-white/60 text-[10px] font-medium mb-1"
              labelFormatter={(value) => value}
              formatter={(value, name) => {
                // Handle both 'price' and 'value' keys, and ensure we get the numeric value
                const priceValue = typeof value === 'number' ? value : Number(value);
                if (!isNaN(priceValue)) {
                  return [
                    <span key="price" className="text-white font-mono font-semibold text-sm">
                      ${priceValue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                    </span>,
                    'Price'
                  ];
                }
                return [value, name];
              }}
              indicator="line"
            />
          }
        />
        <Area
          dataKey="price"
          type="monotone"
          fill={`url(#${gradientId})`}
          stroke={lineColor}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: lineColor }}
        />
      </AreaChart>
    </ChartContainer>
  );
}

type LiveChartData = {
  chartData: Array<{ time: string; price: number }>;
  livePrice: number;
  priceChange: number;
  percentChange: string;
  isCurrentGreen: boolean;
  minPrice: number;
  maxPrice: number;
  gradientColor: string;
};

function useLivePriceChart(): LiveChartData {
  const [livePrice, setLivePrice] = useState(historicalPrices[historicalPrices.length - 1]);
  const timeLabels = useMemo(() => generateTimeLabels(historicalPrices.length), []);
  const historicalChartData = useMemo(
    () =>
      historicalPrices.map((price, index) => ({
        time: timeLabels[index],
        price,
      })),
    [timeLabels],
  );

  const prevPriceRef = useRef(historicalPrices[historicalPrices.length - 1]);
  const deltaIndexRef = useRef(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLivePrice((current) => {
        const delta = liveDeltaSequence[deltaIndexRef.current];
        deltaIndexRef.current = (deltaIndexRef.current + 1) % liveDeltaSequence.length;
        const nextPrice = livePriceClamp(current + delta);
        prevPriceRef.current = current;
        return nextPrice;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const chartData = [...historicalChartData, { time: 'NOW', price: livePrice }];
  const priceChange = livePrice - prevPriceRef.current;
  const percentChange = (((livePrice - historicalPrices[0]) / historicalPrices[0]) * 100).toFixed(2);
  const isCurrentGreen = priceChange >= 0;
  const allPrices = chartData.map((d) => d.price);
  const minPrice = Math.min(...allPrices) - 80;
  const maxPrice = Math.max(...allPrices) + 80;
  const gradientColor = isCurrentGreen ? '#10b981' : '#ef4444';

  return {
    chartData,
    livePrice,
    priceChange,
    percentChange,
    isCurrentGreen,
    minPrice,
    maxPrice,
    gradientColor,
  };
}

export function LivePriceChart() {
  const {
    chartData,
    livePrice,
    priceChange,
    percentChange,
    isCurrentGreen,
    minPrice,
    maxPrice,
    gradientColor,
  } = useLivePriceChart();

  return (
    <div className="w-full h-full flex flex-col">
      <LivePriceHeader
        currentPrice={livePrice}
        priceChange={priceChange}
        percentChange={percentChange}
        isCurrentGreen={isCurrentGreen}
      />
      <div className="flex-1 min-h-0 px-2">
        <ChartVisualization
          chartData={chartData}
          minPrice={minPrice}
          maxPrice={maxPrice}
          gradientColor={gradientColor}
        />
      </div>
    </div>
  );
}

