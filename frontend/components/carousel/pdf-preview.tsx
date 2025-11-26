'use client';

import { motion } from 'framer-motion';

export function PDFPreview() {
  return (
    <div className="w-full h-full flex items-center justify-center p-4">
      <motion.div 
        className="bg-gradient-to-br from-white/10 to-white/5 rounded-xl p-5 w-full max-w-[200px] border border-white/20 shadow-2xl"
        initial={{ rotateY: -5, rotateX: 5 }}
        animate={{ 
          rotateY: [-5, 5, -5],
          rotateX: [5, -5, 5]
        }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500/80 to-red-600/80 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            </svg>
          </div>
          <div>
            <div className="text-xs font-medium text-white">Scorecard.pdf</div>
            <div className="text-[9px] text-white/40">2025-11-12</div>
          </div>
        </div>
        <div className="space-y-2.5">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-white/50">Profit</span>
            <span className="text-sm font-semibold text-emerald-400 font-mono">+18.4%</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-white/50">Drawdown</span>
            <span className="text-sm font-semibold text-red-400 font-mono">-6.1%</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-white/50">Win Rate</span>
            <span className="text-sm font-semibold text-white font-mono">67%</span>
          </div>
          <div className="h-px bg-white/10 my-2" />
          <div className="text-[8px] text-white/30 leading-relaxed font-mono">
            Trace: RSI=28, oversold...
          </div>
        </div>
      </motion.div>
    </div>
  );
}

