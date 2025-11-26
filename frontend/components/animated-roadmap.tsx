'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import createGlobe, { COBEOptions } from 'cobe';
import { cn } from '@/lib/utils';

interface RoadmapStep {
  id: number;
  title: string;
  description: string;
  icon: string;
  location: [number, number]; // [lat, lng]
  color: [number, number, number]; // RGB 0-1
}

const steps: RoadmapStep[] = [
  {
    id: 1,
    title: 'Configure Your Fighter',
    description: 'Pick an LLM, choose Monk or Omni mode, describe your strategy in plain English.',
    icon: '⚙️',
    // West on equatorial band
    location: [15, -60],
    color: [34 / 255, 197 / 255, 94 / 255], // green
  },
  {
    id: 2,
    title: 'Enter The Arena',
    description: 'Your agent battles historical markets with pre-computed indicators & live reasoning logs.',
    icon: '⚔️',
    // Slightly east
    location: [15, -20],
    color: [245 / 255, 158 / 255, 11 / 255], // amber
  },
  {
    id: 3,
    title: 'Get Your Scorecard',
    description: 'PnL, drawdown, win rate — plus a PDF trace of every trade decision.',
    icon: '📊',
    // Further east
    location: [15, 20],
    color: [139 / 255, 92 / 255, 246 / 255], // violet
  },
  {
    id: 4,
    title: 'Go Live (Paper)',
    description: 'Passed the backtest? Forward-test on real-time data without risking capital.',
    icon: '🚀',
    // Far east on same band
    location: [15, 60],
    color: [6 / 255, 182 / 255, 212 / 255], // cyan
  },
];

// Arc overlay component - draws a smooth arc between two 2D points
function ArcOverlay({
  fromPos,
  toPos,
  color,
  containerSize,
  opacity = 1,
}: {
  fromPos: { x: number; y: number };
  toPos: { x: number; y: number };
  color: [number, number, number];
  containerSize: number;
  opacity?: number;
}) {
  const colorStr = `rgb(${color[0] * 255}, ${color[1] * 255}, ${color[2] * 255})`;
  
  const startX = fromPos.x;
  const startY = fromPos.y;
  const endX = toPos.x;
  const endY = toPos.y;
  
  // Calculate arc control point – prefer east/west sweep instead of straight up/down
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;
  const dx = endX - startX;
  const dy = endY - startY;
  const distance = Math.sqrt(dx * dx + dy * dy);

  let controlX = midX;
  let controlY = midY;

  // If points are mostly horizontal, arc upwards.
  // If points are mostly vertical (like 2 → 3), arc sideways (east/west) instead of north/south.
  if (Math.abs(dx) >= Math.abs(dy)) {
    const arcHeight = distance * 0.35;
    controlY = Math.min(startY, endY) - arcHeight;
  } else {
    const arcOffset = distance * 0.35;
    controlX = midX + (dx >= 0 ? arcOffset : -arcOffset);
  }
  
  const arcPath = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
  
  return (
    <svg
      className="w-full h-full pointer-events-none"
      viewBox={`0 0 ${containerSize} ${containerSize}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ position: 'absolute', inset: 0 }}
    >
      <defs>
        <linearGradient id={`arc-gradient-live`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={colorStr} stopOpacity="0.3" />
          <stop offset="50%" stopColor={colorStr} stopOpacity="1" />
          <stop offset="100%" stopColor={colorStr} stopOpacity="0.3" />
        </linearGradient>
        
        <filter id="arc-glow-live">
          <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      {/* Arc line with glow */}
      <motion.path
        d={arcPath}
        fill="none"
        stroke={`url(#arc-gradient-live)`}
        strokeWidth="4"
        strokeLinecap="round"
        filter="url(#arc-glow-live)"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: opacity }}
        exit={{ opacity: 0 }}
        transition={{ duration: 1.5, ease: [0.22, 1, 0.36, 1] }}
      />
      
      {/* Traveling dot */}
      <motion.circle
        r="6"
        fill={colorStr}
        filter="drop-shadow(0 0 10px rgba(255,255,255,0.9))"
        initial={{ offsetDistance: '0%', opacity: 0 }}
        animate={{ 
          offsetDistance: '100%', 
          opacity: [0, opacity, opacity, opacity, 0] 
        }}
        transition={{ duration: 2, ease: [0.22, 1, 0.36, 1] }}
        style={{
          offsetPath: `path('${arcPath}')`,
        }}
      />
    </svg>
  );
}

function StepGlobe({
  activeStep,
  previousStep,
  className,
}: {
  activeStep: number;
  previousStep: number;
  className?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Static globe – purely visual background
  useEffect(() => {
    if (!canvasRef.current) return;

    const config: COBEOptions = {
      devicePixelRatio: 2,
      width: 800,
      height: 800,
      phi: 0,
      theta: 0.25,
      dark: 1,
      diffuse: 0.8,
      mapSamples: 16000,
      mapBrightness: 1.2,
      baseColor: [0.1, 0.1, 0.1],
      markerColor: [1, 1, 1],
      glowColor: [0.08, 0.08, 0.12],
      markers: [],
      onRender: () => {},
    };

    const globe = createGlobe(canvasRef.current, config);
    setTimeout(() => {
      if (canvasRef.current) {
        canvasRef.current.style.opacity = '1';
      }
    }, 0);

    return () => {
      globe.destroy();
    };
  }, []);

  // Fixed 2D pin positions over the globe (in px within a 600x600 viewBox)
  const containerSize = 600;
  const uiPins: Record<number, { x: number; y: number }> = {
    1: { x: containerSize * 0.32, y: containerSize * 0.6 },
    2: { x: containerSize * 0.45, y: containerSize * 0.52 },
    3: { x: containerSize * 0.6, y: containerSize * 0.52 },
    4: { x: containerSize * 0.72, y: containerSize * 0.6 },
  };

  const fromPos = uiPins[previousStep];
  const toPos = uiPins[activeStep];

  return (
    <div className={cn('absolute inset-0 mx-auto aspect-[1/1] w-full max-w-[600px]', className)}>
      <canvas
        className="size-full opacity-0 transition-opacity duration-500 [contain:layout_paint_size] relative z-0"
        ref={canvasRef}
      />

      {/* Single clear arc from previous step to active step */}
      <div className="absolute inset-0 z-10 pointer-events-none">
        {fromPos && toPos && (
          <ArcOverlay
            fromPos={fromPos}
            toPos={toPos}
            color={steps[activeStep - 1].color}
            containerSize={containerSize}
            opacity={1}
          />
        )}
      </div>
    </div>
  );
}

export function AnimatedRoadmap() {
  const [activeStep, setActiveStep] = useState(1);
  const [previousStep, setPreviousStep] = useState(1);
  const [isAnimating, setIsAnimating] = useState(true);

  // Auto-cycle steps - stay longer on each step
  useEffect(() => {
    if (!isAnimating) return;
    const id = setInterval(() => {
      setActiveStep((prev) => {
        setPreviousStep(prev);
        return (prev % steps.length) + 1;
      });
    }, 5000); // Increased from 3200 to 5000ms
    return () => clearInterval(id);
  }, [isAnimating]);

  const activeStepData = steps[activeStep - 1];

  const handleStepClick = (stepId: number) => {
    setIsAnimating(false);
    setPreviousStep(activeStep);
    setActiveStep(stepId);
  };

  return (
    <div
      className="h-full p-6 md:p-8 flex flex-col overflow-hidden relative"
      onMouseEnter={() => setIsAnimating(false)}
      onMouseLeave={() => setIsAnimating(true)}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="mb-4 z-10"
      >
        <p className="text-[10px] uppercase tracking-[0.25em] text-violet-400/60 mb-1.5 font-medium">
          How It Works
        </p>
        <h3 className="text-lg md:text-xl font-semibold text-white font-[family-name:var(--font-syne)]">
          Your Global Journey
        </h3>
      </motion.div>

      {/* Globe + Info Layout */}
      <div className="flex-1 flex items-center justify-between gap-8 relative">
        {/* Globe */}
        <div className="flex-1 relative h-full flex items-center justify-center">
          <StepGlobe activeStep={activeStep} previousStep={previousStep} />
        </div>

        {/* Step Info Card */}
        <motion.div
          key={activeStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 0.9, 0.25, 1] }}
          className="w-[300px] z-10"
        >
          <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] border border-white/20 rounded-2xl p-6 backdrop-blur-sm">
            {/* Step Number */}
            <div className="mb-3">
              <span className="text-[10px] font-bold text-violet-400 tracking-wider">
                STEP {activeStepData.id} OF {steps.length}
              </span>
            </div>

            {/* Icon */}
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center border-2"
                style={{
                  backgroundColor: `rgba(${activeStepData.color[0] * 255}, ${activeStepData.color[1] * 255}, ${activeStepData.color[2] * 255}, 0.2)`,
                  borderColor: `rgb(${activeStepData.color[0] * 255}, ${activeStepData.color[1] * 255}, ${activeStepData.color[2] * 255})`,
                }}
              >
                <span className="text-2xl">{activeStepData.icon}</span>
              </div>
              <h4 className="text-base font-bold text-white font-[family-name:var(--font-syne)] flex-1">
                {activeStepData.title}
              </h4>
            </div>

            {/* Description */}
            <p className="text-xs text-white/70 leading-relaxed">{activeStepData.description}</p>
          </div>
        </motion.div>
      </div>

      {/* Step Indicators - Bottom */}
      <div className="flex items-center justify-center gap-4 mt-6 z-10">
        {steps.map((step) => {
          const isActive = step.id === activeStep;

          return (
            <button
              key={step.id}
              onClick={() => handleStepClick(step.id)}
              className="group relative flex flex-col items-center gap-1.5 transition-all"
              aria-label={`Go to step ${step.id}: ${step.title}`}
            >
              {/* Circle */}
              <motion.div
                className="relative w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all"
                style={{
                  backgroundColor: isActive
                    ? `rgba(${step.color[0] * 255}, ${step.color[1] * 255}, ${step.color[2] * 255}, 0.2)`
                    : 'rgba(255, 255, 255, 0.05)',
                  borderColor: isActive
                    ? `rgb(${step.color[0] * 255}, ${step.color[1] * 255}, ${step.color[2] * 255})`
                    : 'rgba(255, 255, 255, 0.2)',
                }}
                animate={{
                  scale: isActive ? 1.1 : 1,
                }}
                whileHover={{
                  scale: isActive ? 1.1 : 1.05,
                }}
                transition={{ duration: 0.2 }}
              >
                <span className="text-lg">{step.icon}</span>

                {/* Active pulse */}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    style={{
                      backgroundColor: `rgba(${step.color[0] * 255}, ${step.color[1] * 255}, ${step.color[2] * 255}, 0.3)`,
                    }}
                    initial={{ scale: 1, opacity: 0.5 }}
                    animate={{ scale: 1.5, opacity: 0 }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      ease: 'easeOut',
                    }}
                  />
                )}
              </motion.div>

              {/* Label */}
              <span
                className={`text-[9px] font-medium transition-all ${
                  isActive ? 'text-white' : 'text-white/40 group-hover:text-white/60'
                }`}
              >
                {step.id}
              </span>
            </button>
          );
        })}
      </div>

      {/* Footer hint */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-[9px] text-white/30 text-center mt-3"
      >
        {isAnimating ? 'Auto-playing • Hover to pause' : 'Click any step • Drag to rotate globe'}
      </motion.p>
    </div>
  );
}
