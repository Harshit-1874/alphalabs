'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Carousel } from './carousel';
import { Marquee } from './ui/marquee';
import { AnimatedRoadmap } from './animated-roadmap';
import { useState } from 'react';
import Link from 'next/link';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.5,
      ease: [0.22, 0.9, 0.25, 1] as [number, number, number, number],
    },
  },
};


// Indicator chip for marquee
function IndicatorChip({ name, value }: { name: string; value: string }) {
  return (
    <div className="flex items-center gap-2 bg-gradient-to-br from-white/[0.08] to-white/[0.02] border border-white/10 px-3 py-2 rounded-lg hover:border-violet-500/40 transition-colors cursor-default">
      <span className="text-xs font-medium text-white/80">{name}</span>
      {value !== '—' && (
        <span className="text-xs text-violet-400 font-mono">{value}</span>
      )}
    </div>
  );
}

// Tile C - Indicator Buffet with Marquee
function TileIndicatorBuffet() {
  const indicators = [
    { name: 'RSI (14)', value: '42.1' },
    { name: 'MACD (12,26)', value: '-0.013' },
    { name: 'ATR (14)', value: '1.32' },
    { name: 'EMA (20)', value: '44.2k' },
    { name: 'EMA (50)', value: '43.8k' },
    { name: 'EMA (200)', value: '41.5k' },
    { name: 'SMA (50)', value: '43.9k' },
    { name: 'Bollinger', value: '±2.1%' },
    { name: 'VWAP', value: '46,200' },
    { name: 'ADX', value: '24.5' },
    { name: 'SAR', value: '42.8k' },
    { name: 'OBV', value: '1.2M' },
  ];

  return (
    <div className="h-full p-5 flex flex-col overflow-hidden">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h3 className="text-base font-semibold text-white mb-0.5 font-[family-name:var(--font-syne)]">
          Market Data Inputs
        </h3>
        <p className="text-[11px] text-white/50 mb-3">
          Your model receives structured signals without needing custom data pipelines.
        </p>
      </motion.div>
      
      {/* Marquee container */}
      <div className="flex-1 relative overflow-hidden -mx-5">
        <div className="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-black/80 to-transparent z-10 pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-black/80 to-transparent z-10 pointer-events-none" />
        
        <Marquee pauseOnHover duration={25} className="py-2">
          {indicators.map((ind) => (
            <IndicatorChip key={ind.name} name={ind.name} value={ind.value} />
          ))}
        </Marquee>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <Link
          href="/indicators/customize"
          className="inline-flex items-center gap-1 mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors group"
        >
          Customize indicator JSON
          <svg className="w-3 h-3 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </motion.div>
    </div>
  );
}

// Tile D - Developer Tools
function TileDeveloperTools() {
  const [copied, setCopied] = useState(false);
  
  const exampleJson = `{
  "name": "custom_feature",
  "formula": "(close - ema_50) / atr_14",
  "description": "Normalized deviation vs 50-period EMA"
}`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(exampleJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="h-full p-5 flex flex-col">
      <h3 className="text-base font-semibold text-white mb-0.5 font-[family-name:var(--font-syne)]">
        Developer Tools
      </h3>
      <p className="text-[11px] text-white/50 mb-3">
        Customize your model's inputs and create lightweight computed features using safe JSON formulas.
      </p>
      
      {/* Code block */}
      <div className="relative flex-1 bg-black/40 rounded-xl border border-white/10 overflow-hidden">
        <div className="absolute top-2 right-2 z-10">
          <motion.button
            onClick={handleCopy}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none"
            aria-label="Copy formula"
            whileTap={{ scale: 0.95 }}
          >
            {copied ? (
              <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5 text-white/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </motion.button>
        </div>
        <pre className="p-4 text-[11px] font-mono text-white/70 overflow-x-auto whitespace-pre leading-relaxed">
          <code>
            <span className="text-white/30">{'{'}</span>{'\n'}
            {'  '}<span className="text-violet-400">"name"</span>: <span className="text-emerald-400">"custom_feature"</span>,{'\n'}
            {'  '}<span className="text-violet-400">"formula"</span>: <span className="text-emerald-400">"(close - ema_50) / atr_14"</span>,{'\n'}
            {'  '}<span className="text-violet-400">"description"</span>: <span className="text-emerald-400">"Normalized deviation..."</span>{'\n'}
            <span className="text-white/30">{'}'}</span>
          </code>
        </pre>
      </div>

      {/* Copy feedback toast */}
      <AnimatePresence>
        {copied && (
          <motion.div
            className="absolute bottom-20 right-6 bg-emerald-500/90 text-white text-xs px-3 py-1.5 rounded-full font-medium shadow-lg"
            initial={{ opacity: 0, y: 10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            transition={{ duration: 0.2 }}
          >
            ✓ Copied!
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center justify-between mt-3">
        <Link
          href="/indicators/create"
          className="inline-flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 transition-colors group"
        >
          Create custom feature
          <svg className="w-3.5 h-3.5 transition-transform group-hover:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </Link>
      </div>
      
      <p className="text-[9px] text-white/30 mt-2 leading-relaxed">
        We parse formulas safely and compute server-side; no code execution from users is allowed.
      </p>
    </div>
  );
}

// Tile E - Scorecards & Reasoning
function TileScorecardsReasoning() {
  const reasoningSnippet = `Simulated trades: 128
Trade list and timestamps
Reasoning trace
PnL curve`;

  return (
    <div className="h-full p-5 flex flex-col">
      <h3 className="text-base font-semibold text-white mb-0.5 font-[family-name:var(--font-syne)]">
        Results and Insights
      </h3>
      <p className="text-[11px] text-white/50 mb-3">
        After each simulation AlphaLab shows how your model behaved.
      </p>
      
      {/* Visual - side by side thumbnails */}
      <div className="flex-1 flex gap-3">
        {/* PDF thumbnail */}
        <motion.div 
          className="flex-1 bg-gradient-to-br from-red-500/10 to-red-500/5 rounded-xl border border-red-500/20 p-3 flex flex-col items-center justify-center cursor-pointer"
          whileHover={{ scale: 1.02, borderColor: 'rgba(239, 68, 68, 0.4)' }}
          transition={{ duration: 0.2 }}
        >
          <svg className="w-10 h-10 text-red-400/70 mb-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14,2 14,8 20,8" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5"/>
          </svg>
          <span className="text-[10px] text-white/50 font-medium">Scorecard.pdf</span>
        </motion.div>
        
        {/* Reasoning trace */}
        <div className="flex-1 bg-black/40 rounded-xl border border-white/10 p-3 overflow-hidden">
          <div className="text-[8px] font-mono text-white/50 leading-relaxed whitespace-pre-wrap">
            {reasoningSnippet}
          </div>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {['Trade list', 'Reasoning trace', 'PnL metrics'].map((tag) => (
          <span
            key={tag}
            className="text-[9px] text-white/40 bg-white/5 px-2 py-0.5 rounded-md border border-white/5"
          >
            {tag}
          </span>
        ))}
      </div>

      <Link
        href="/example-results"
        className="inline-flex items-center gap-1 mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors group"
      >
        View example results
        <svg className="w-3 h-3 transition-transform group-hover:translate-y-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      </Link>
    </div>
  );
}

// Tile F - Safety & Controls
function TileSafetyControls() {
  const [safetyEnabled, setSafetyEnabled] = useState(true);

  const safetyFeatures = [
    { text: 'Throttled trading frequency', icon: '📊' },
    { text: 'Controlled environment for experimentation', icon: '🛡️' },
    { text: 'Dummy cash prevents real losses', icon: '⏱️' },
  ];

  return (
    <div className="h-full p-5 flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-white mb-0.5 font-[family-name:var(--font-syne)]">
            Safety & Controls
          </h3>
        </div>
        
        {/* Toggle */}
        <motion.button
          onClick={() => setSafetyEnabled(!safetyEnabled)}
          className={`relative w-12 h-6 rounded-full transition-colors ${
            safetyEnabled ? 'bg-emerald-500' : 'bg-white/20'
          } focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none`}
          aria-label={`Safety mode ${safetyEnabled ? 'enabled' : 'disabled'}`}
          role="switch"
          aria-checked={safetyEnabled}
          whileTap={{ scale: 0.95 }}
        >
          <motion.div
            className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-md"
            animate={{ left: safetyEnabled ? 26 : 4 }}
            transition={{ duration: 0.2, ease: [0.22, 0.9, 0.25, 1] }}
          />
        </motion.button>
      </div>

      <ul className="flex-1 space-y-3">
        {safetyFeatures.map((feature, index) => (
          <motion.li
            key={index}
            className="flex items-start gap-2.5 text-xs text-white/60"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.1 }}
          >
            <span className="text-sm">{feature.icon}</span>
            <span className="leading-relaxed">{feature.text}</span>
          </motion.li>
        ))}
      </ul>

      <p className="text-[9px] text-white/30 mt-3 leading-relaxed border-t border-white/5 pt-3">
        All safety rules are enforced by the backend referee and cannot be disabled by the agent.
      </p>

      <Link
        href="/safety-settings"
        className="inline-flex items-center gap-1 mt-2 text-xs text-violet-400 hover:text-violet-300 transition-colors group"
      >
        View safety settings
        <svg className="w-3 h-3 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </Link>
    </div>
  );
}

// Footer CTA
function FooterCTA() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.5 }}
      className="text-center py-10"
    >
      <p className="text-sm text-white/50 mb-4">
        Ready to test your model?
      </p>
      <Link
        href="/example-results"
        className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-white bg-gradient-to-r from-white/5 to-white/[0.02] border border-white/15 rounded-full hover:bg-white/10 hover:border-white/25 transition-all focus-visible:ring-4 focus-visible:ring-white/20 focus-visible:outline-none group"
      >
        View example results
        <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </Link>
    </motion.div>
  );
}

export function BentoGrid() {
  return (
    <div className="space-y-5 md:space-y-6">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-4 md:space-y-5"
      >
        {/* Tile A - Simple minimalist placeholder - Full width */}
        <motion.div
          variants={itemVariants}
          className="w-full min-h-[120px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300 flex items-center justify-center p-6"
        >
          <div className="text-center">
            <h3 className="text-lg font-semibold text-white mb-2 font-[family-name:var(--font-syne)]">
              How it works
            </h3>
            <p className="text-sm text-white/50">
              Coming soon
            </p>
          </div>
        </motion.div>

        {/* Rest of the tiles in a grid layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[minmax(200px,auto)] gap-4 md:gap-5">
          {/* Tile B - Carousel (2 cols, 2 rows) */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 lg:row-span-2 min-h-[400px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300"
            role="region"
            aria-label="Features carousel"
          >
            <Carousel />
          </motion.div>

          {/* Tile C - Indicator Buffet (fills space next to Carousel, row 1) */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 min-h-[200px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300"
          >
            <TileIndicatorBuffet />
          </motion.div>

          {/* Tile D - Developer Tools (fills space next to Carousel, row 2) */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 min-h-[200px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300 relative"
          >
            <TileDeveloperTools />
          </motion.div>

          {/* Tile E - Scorecards & Reasoning (full width below) */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 min-h-[200px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300"
          >
            <TileScorecardsReasoning />
          </motion.div>

          {/* Tile F - Safety & Controls (full width below) */}
          <motion.div
            variants={itemVariants}
            className="lg:col-span-2 min-h-[200px] bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10 rounded-2xl backdrop-blur-sm overflow-hidden hover:border-white/15 transition-colors duration-300"
          >
            <TileSafetyControls />
          </motion.div>
        </div>
      </motion.div>

      {/* Footer CTA */}
      <FooterCTA />
    </div>
  );
}
