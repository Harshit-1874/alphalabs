'use client';

import { motion } from 'framer-motion';

export function IndicatorChips() {
  const indicators = [
    { name: 'RSI', value: '42' },
    { name: 'MACD', value: '-0.01' },
    { name: 'ATR', value: '1.32' },
    { name: 'VWAP', value: '46.2k' },
    { name: 'SMA', value: '—' },
    { name: 'EMA', value: '—' },
    { name: 'BB', value: '—' },
    { name: 'ADX', value: '24' },
  ];
  
  return (
    <div className="w-full h-full flex items-center justify-center p-4 overflow-hidden">
      <div className="flex flex-wrap gap-2 justify-center">
        {indicators.map((ind, index) => (
          <motion.div
            key={ind.name}
            className="bg-gradient-to-br from-white/10 to-white/5 border border-white/20 px-3 py-2 rounded-lg flex items-center gap-2 shadow-lg"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ 
              duration: 0.4, 
              delay: index * 0.05,
              ease: [0.22, 0.9, 0.25, 1]
            }}
            whileHover={{ scale: 1.05, borderColor: 'rgba(139, 92, 246, 0.5)' }}
          >
            <span className="text-xs font-medium text-white/80">{ind.name}</span>
            <span className="text-xs text-violet-400 font-mono">{ind.value}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

