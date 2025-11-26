'use client';

import { motion } from 'framer-motion';

export function ModesCompare() {
  return (
    <div className="w-full h-full flex items-center justify-center p-4 gap-4">
      <motion.div 
        className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/30 rounded-xl p-4 flex-1 max-w-[140px]"
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        whileHover={{ scale: 1.02, borderColor: 'rgba(59, 130, 246, 0.5)' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-blue-500 rounded-md flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <span className="text-xs font-semibold text-white">Math-only</span>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-[10px] text-white/60">
            <span className="text-blue-400">✓</span> Price data
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-white/60">
            <span className="text-blue-400">✓</span> Indicators
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-white/30">
            <span>✗</span> No news
          </div>
        </div>
      </motion.div>

      <div className="text-white/20 text-xs font-bold">VS</div>

      <motion.div 
        className="bg-gradient-to-br from-violet-500/10 to-violet-500/5 border border-violet-500/30 rounded-xl p-4 flex-1 max-w-[140px]"
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        whileHover={{ scale: 1.02, borderColor: 'rgba(139, 92, 246, 0.5)' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-violet-500 rounded-md flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
            </svg>
          </div>
          <span className="text-xs font-semibold text-white">Context</span>
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-[10px] text-white/60">
            <span className="text-violet-400">✓</span> Price data
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-white/60">
            <span className="text-violet-400">✓</span> Indicators
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-violet-300">
            <span className="text-violet-400">✓</span> Headlines
          </div>
        </div>
      </motion.div>
    </div>
  );
}

