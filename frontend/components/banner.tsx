'use client';

import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { GetStartedButton } from './get-started-button';

// Animated counter component for metrics
function AnimatedCounter({ 
  value, 
  suffix = '', 
  prefix = '',
  delay = 0 
}: { 
  value: number; 
  suffix?: string; 
  prefix?: string;
  delay?: number;
}) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => {
    if (Math.abs(value) < 1) {
      return latest.toFixed(1);
    }
    return Math.round(latest).toString();
  });
  const [displayValue, setDisplayValue] = useState('—');
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    // Check for reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    if (mediaQuery.matches) {
      setDisplayValue(`${prefix}${Math.abs(value) < 1 ? value.toFixed(1) : value}${suffix}`);
      return;
    }

    const timeout = setTimeout(() => {
      const controls = animate(count, value, {
        duration: 0.8,
        ease: [0.22, 0.9, 0.25, 1],
      });

      const unsubscribe = rounded.on('change', (v) => {
        setDisplayValue(`${prefix}${v}${suffix}`);
      });

      return () => {
        controls.stop();
        unsubscribe();
      };
    }, delay * 1000);

    return () => clearTimeout(timeout);
  }, [count, rounded, value, prefix, suffix, delay]);

  return <span className="font-mono tabular-nums">{displayValue}</span>;
}

// Simulation Replay Preview card component
function SimulationReplayCard() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="relative bg-gradient-to-br from-white/10 to-white/5 border border-white/20 rounded-lg p-4 backdrop-blur-sm cursor-pointer"
      style={{ aspectRatio: '4/3', minWidth: '200px', maxWidth: '240px' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      animate={{
        y: isHovered ? -6 : 0,
        boxShadow: isHovered 
          ? '0 20px 40px rgba(139, 92, 246, 0.3), 0 0 60px rgba(139, 92, 246, 0.15)'
          : '0 4px 20px rgba(0, 0, 0, 0.3)',
      }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      {/* Replay speed badge */}
      <div className="absolute -top-2 -right-2 bg-violet-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
        Replay speed 4x
      </div>

      {/* Header */}
      <div className="border-b border-white/10 pb-2 mb-3">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-4 rounded-full bg-gradient-to-br from-violet-400 to-fuchsia-500" />
          <span className="text-[10px] text-white/50 uppercase tracking-widest font-medium">AlphaLab</span>
        </div>
        <h4 className="text-sm font-semibold text-white">Simulation Replay Preview</h4>
      </div>

      {/* Metadata */}
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-white/50">Period</span>
          <span className="text-white/80 font-mono">2020 to 2022 BTCUSD</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-white/50">Replay speed</span>
          <span className="bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded text-[10px]">4x</span>
        </div>
      </div>

      {/* View link */}
      <div className="mt-3 pt-2 border-t border-white/10">
        <a 
          href="#" 
          className="text-[10px] text-violet-400 hover:text-violet-300 transition-colors underline underline-offset-2"
          onClick={(e) => e.preventDefault()}
        >
          View replay
        </a>
      </div>
    </motion.div>
  );
}

// Model Behavior Snapshot component
function ModelBehaviorSnapshot() {
  const metrics = [
    { label: 'Simulated trades', value: 128, prefix: '', suffix: '' },
    { label: 'Live paper trading', value: 1, prefix: '', suffix: '', isActive: true },
  ];

  return (
    <motion.div
      className="bg-white/5 border border-white/10 rounded-lg p-4 backdrop-blur-sm"
      style={{ minWidth: '180px', maxWidth: '200px' }}
    >
      <h4 className="text-xs text-white/50 uppercase tracking-widest mb-3 font-medium">Model Behavior</h4>
      <div className="space-y-3">
        {metrics.map((metric, index) => (
          <div key={metric.label} className="flex justify-between items-baseline">
            <span className="text-xs text-white/60">{metric.label}</span>
            <span className={`text-lg font-semibold ${
              metric.isActive ? 'text-emerald-400' : 'text-white'
            }`}>
              {metric.isActive ? (
                <span className="text-emerald-400">Active</span>
              ) : (
                <AnimatedCounter 
                  value={metric.value} 
                  prefix={metric.prefix}
                  suffix={metric.suffix}
                  delay={0.12 * index}
                />
              )}
            </span>
          </div>
        ))}
        <div className="pt-2 border-t border-white/5">
          <p className="text-[10px] text-white/50 italic leading-relaxed">
            Model: Considering long entry due to rising volume
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export function Banner() {
  return (
    <motion.section
      className="w-full bg-gradient-to-b from-white/[0.03] to-transparent border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, delay: 0.12, ease: [0.22, 0.9, 0.25, 1] }}
      role="banner"
      aria-label="AlphaLab hero section"
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 p-6 md:p-8 lg:p-10">
        {/* Left side - Content */}
        <div className="flex flex-col justify-center space-y-6">
          {/* Kicker */}
          <motion.p 
            className="text-xs text-white/50 uppercase tracking-[0.2em] font-medium"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.18 }}
          >
            Bring your model · Connect your key · Test in real markets
          </motion.p>

          {/* Headline */}
          <motion.h1 
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-white leading-tight font-[family-name:var(--font-syne)]"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.24 }}
          >
            Test your AI trading agent in real market conditions
          </motion.h1>

          {/* Subhead */}
          <motion.h2 
            className="text-base md:text-lg text-white/70 leading-relaxed max-w-xl"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.30 }}
          >
            Bring your model, connect your own key, run historical simulations and live paper trading with dummy cash using full real market data inputs.
          </motion.h2>

          {/* CTAs */}
          <motion.div 
            className="flex flex-col sm:flex-row gap-3 pt-2"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.36 }}
          >
            <GetStartedButton />
            <Link
              href="/example-results"
              className="inline-flex items-center justify-center gap-2 px-6 py-4 text-base font-medium text-white/60 hover:text-white/80 bg-white/[0.02] border border-white/8 rounded-full backdrop-blur-sm transition-all hover:bg-white/[0.04] hover:border-white/12"
            >
              View example results
            </Link>
          </motion.div>

          {/* Microcopy */}
          <motion.p 
            className="text-[11px] text-white/40 max-w-md leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.42, delay: 0.42 }}
          >
            AlphaLab gives your agent complete market signals including indicators, volume, sentiment and news.
          </motion.p>
        </div>

        {/* Right side - Visual composition */}
        <motion.div 
          className="flex flex-col md:flex-row lg:flex-col xl:flex-row items-center justify-center gap-4 py-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.42, delay: 0.30 }}
        >
          <SimulationReplayCard />
          <ModelBehaviorSnapshot />
        </motion.div>
      </div>
    </motion.section>
  );
}
