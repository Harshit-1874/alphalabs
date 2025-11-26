'use client';

import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useState } from 'react';

export function GetStartedButton() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="flex justify-center"
    >
      <div className="relative">
        {/* Anime Mascot - Absolutely positioned above right */}
        <motion.div
          className="absolute -top-10 -right-2 pointer-events-none z-10"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          <div className="relative w-8 h-8">
            <motion.div 
              className="absolute w-7 h-7 bg-white rounded-full left-1/2 -translate-x-1/2"
              animate={
                isHovered ? {
                  scale: [1, 1.1, 1],
                  rotate: [0, -5, 5, 0],
                  transition: {
                    duration: 0.5,
                    ease: "easeInOut"
                  }
                } : {
                  y: [0, -2, 0],
                  transition: {
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }
                }
              }
            >
              {/* Left eye */}
              <motion.div 
                className="absolute w-1.5 h-1.5 bg-black rounded-full"
                animate={
                  isHovered ? {
                    scaleY: [1, 0.2, 1],
                    transition: { duration: 0.2, times: [0, 0.5, 1] }
                  } : {}
                }
                style={{ left: '22%', top: '38%' }}
              />
              {/* Right eye */}
              <motion.div 
                className="absolute w-1.5 h-1.5 bg-black rounded-full"
                animate={
                  isHovered ? {
                    scaleY: [1, 0.2, 1],
                    transition: { duration: 0.2, times: [0, 0.5, 1] }
                  } : {}
                }
                style={{ right: '22%', top: '38%' }}
              />
              {/* Left blush */}
              <motion.div 
                className="absolute w-1.5 h-1 bg-pink-300 rounded-full"
                animate={{ opacity: isHovered ? 0.8 : 0.6 }}
                style={{ left: '12%', top: '55%' }}
              />
              {/* Right blush */}
              <motion.div 
                className="absolute w-1.5 h-1 bg-pink-300 rounded-full"
                animate={{ opacity: isHovered ? 0.8 : 0.6 }}
                style={{ right: '12%', top: '55%' }}
              />
              {/* Mouth */}
              <motion.div 
                className="absolute w-3 h-1.5 border-b-[1.5px] border-black rounded-full"
                animate={isHovered ? { scaleY: 1.5, y: -1 } : { scaleY: 1, y: 0 }}
                style={{ left: '28%', top: '58%' }}
              />
              {/* Sparkles */}
              <AnimatePresence>
                {isHovered && (
                  <>
                    <motion.span
                      initial={{ opacity: 0, scale: 0 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0 }}
                      className="absolute -top-1 -right-1 text-[8px]"
                    >
                      ✨
                    </motion.span>
                    <motion.span
                      initial={{ opacity: 0, scale: 0 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0 }}
                      transition={{ delay: 0.1 }}
                      className="absolute -top-1.5 -left-0.5 text-[8px]"
                    >
                      ✨
                    </motion.span>
                  </>
                )}
              </AnimatePresence>
            </motion.div>
            {/* Triangle */}
            <motion.div
              className="absolute -bottom-0.5 left-1/2 w-2.5 h-2.5 -translate-x-1/2"
              animate={
                isHovered ? {
                  y: [0, -2, 0],
                  transition: { duration: 0.3, repeat: Infinity, repeatType: "reverse" as const }
                } : {
                  y: [0, 1, 0],
                  transition: { duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.5 }
                }
              }
            >
              <div className="w-full h-full bg-white rotate-45 transform origin-center" />
            </motion.div>
          </div>
        </motion.div>

        {/* Button */}
        <Link
          href="/sign-in"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="relative inline-flex items-center justify-center gap-3 px-8 py-4 text-base font-medium text-white/80 bg-white/[0.03] border border-white/8 rounded-full backdrop-blur-sm font-[family-name:var(--font-syne)]"
        >
          {/* Glow */}
          <motion.div
            className="absolute inset-0 rounded-full -z-10 overflow-hidden"
            animate={{ opacity: [0.2, 0.3, 0.2], scale: [1, 1.03, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <div className="absolute inset-0 bg-white/8 rounded-full blur-md" />
            <div className="absolute inset-[-4px] bg-white/5 rounded-full blur-xl" />
          </motion.div>

          {/* Hover bg */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute inset-0 bg-white/6 rounded-full -z-10"
              />
            )}
          </AnimatePresence>

          {/* Content */}
          <span className="relative z-10 flex items-center gap-3">
            Start testing my model
            <motion.svg 
              className="w-5 h-5" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
              animate={{ x: isHovered ? 4 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </motion.svg>
          </span>
        </Link>
      </div>
    </motion.div>
  );
}
