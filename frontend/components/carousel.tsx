'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { carouselItems } from './carousel/carousel-data';
import { SlideVisual } from './carousel/slide-visual';

export function Carousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [autoplay] = useState(true); // Autoplay ON
  const containerRef = useRef<HTMLDivElement>(null);

  const goToSlide = useCallback((index: number) => {
    setCurrentIndex(index);
  }, []);

  const goToPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev - 1 + carouselItems.length) % carouselItems.length);
  }, []);

  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % carouselItems.length);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!containerRef.current?.contains(document.activeElement)) return;
      
      if (e.key === 'ArrowLeft') {
        goToPrevious();
      } else if (e.key === 'ArrowRight') {
        goToNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToPrevious, goToNext]);

  // Autoplay (optional - OFF by default, 6s per slide, pause on hover/focus)
  useEffect(() => {
    if (!autoplay || isPaused) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % carouselItems.length);
    }, 6000);

    return () => clearInterval(interval);
  }, [autoplay, isPaused]);

  const currentItem = carouselItems[currentIndex];

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full flex flex-col"
      role="region"
      aria-label="Feature carousel"
      aria-roledescription="carousel"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
      tabIndex={0}
    >
      {/* Live region for accessibility */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        Slide {currentIndex + 1} of {carouselItems.length}: {currentItem.title}
      </div>

      {/* Main content area */}
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentItem.id}
            className="absolute inset-0 flex flex-col lg:flex-row"
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.32 }}
          >
            {/* Visual side */}
            <div className="h-40 lg:h-full lg:w-1/2 bg-gradient-to-br from-white/[0.03] to-transparent border-b lg:border-b-0 lg:border-r border-white/10">
              <SlideVisual type={currentItem.visual} />
            </div>

            {/* Content side */}
            <div className="flex-1 p-5 lg:p-6 flex flex-col justify-center">
              <motion.h3 
                className="text-lg lg:text-xl font-semibold text-white mb-1.5 font-[family-name:var(--font-syne)]"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                {currentItem.title}
              </motion.h3>
              <motion.p 
                className="text-sm text-white/60 mb-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                {currentItem.subtitle}
              </motion.p>
              <ul className="space-y-2 mb-5">
                {currentItem.bullets.map((bullet, index) => (
                  <motion.li
                    key={index}
                    className="flex items-start gap-2 text-xs text-white/50"
                    initial={{ opacity: 0, x: 8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + index * 0.05, duration: 0.2 }}
                  >
                    <span className="text-violet-400 mt-0.5">•</span>
                    <span>{bullet}</span>
                  </motion.li>
                ))}
              </ul>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <Link
                  href={currentItem.action.slug}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-violet-400 hover:text-violet-300 transition-colors group"
                >
                  {currentItem.action.label}
                  <svg className="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </motion.div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 left-0 right-0 flex items-center justify-between px-5 z-10">
        {/* Prev button */}
        <motion.button
          onClick={goToPrevious}
          className="p-2 rounded-full bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none"
          aria-label="Previous slide"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </motion.button>

        {/* Dot pagination */}
        <div className="flex gap-2">
          {carouselItems.map((item, index) => (
            <button
              key={item.id}
              onClick={() => goToSlide(index)}
              className={`h-2 rounded-full transition-all duration-300 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none ${
                index === currentIndex
                  ? 'w-8 bg-gradient-to-r from-violet-500 to-fuchsia-500'
                  : 'w-2 bg-white/20 hover:bg-white/40'
              }`}
              aria-label={`Go to slide ${index + 1}: ${item.title}`}
              aria-current={index === currentIndex ? 'true' : undefined}
            />
          ))}
        </div>

        {/* Next button */}
        <motion.button
          onClick={goToNext}
          className="p-2 rounded-full bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none"
          aria-label="Next slide"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </motion.button>
      </div>

      {/* Empty state (hidden but available for no-content scenarios) */}
      {carouselItems.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-white/40">
          No previews available — run a simulation to see results here.
        </div>
      )}
    </div>
  );
}
