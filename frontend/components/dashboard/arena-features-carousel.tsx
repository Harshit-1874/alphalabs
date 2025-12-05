"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Brain, History, Play, ChevronLeft, ChevronRight, ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Feature {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  badge?: string;
  badgeColor: string;
  ctaLink: string;
}

const features: Feature[] = [
  {
    id: "council",
    icon: Brain,
    title: "Council Mode",
    description: "Multiple AI models collaborate through a 3-stage process for robust trading decisions.",
    badge: "NEW",
    badgeColor: "bg-primary/10 text-primary border-primary/20",
    ctaLink: "/dashboard/arena/backtest?council=true",
  },
  {
    id: "backtest",
    icon: History,
    title: "Backtest Arena",
    description: "Test strategies against historical data with detailed metrics and playback controls.",
    badge: undefined,
    badgeColor: "",
    ctaLink: "/dashboard/arena/backtest",
  },
  {
    id: "forward",
    icon: Play,
    title: "Forward Test",
    description: "Paper trade with live data in real-time. Validate strategies with zero risk.",
    badge: "LIVE",
    badgeColor: "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20",
    ctaLink: "/dashboard/arena/forward",
  },
];

export function ArenaFeaturesCarousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const currentFeature = features[currentIndex];

  // Auto-rotate every 5 seconds
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % features.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [isPaused]);

  const goToNext = () => {
    setCurrentIndex((prev) => (prev + 1) % features.length);
  };

  const goToPrev = () => {
    setCurrentIndex((prev) => (prev - 1 + features.length) % features.length);
  };

  const goToIndex = (index: number) => {
    setCurrentIndex(index);
  };

  return (
    <Card 
      className="relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm hover:bg-card transition-colors"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <CardContent className="p-0">
        <div className="relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentFeature.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Link href={currentFeature.ctaLink} className="block group">
                <div className="px-4 py-3 sm:px-5 sm:py-3.5">
                  <div className="flex items-center gap-3 sm:gap-4">
                    {/* Icon & Title - Left */}
                    <div className="flex items-center gap-2.5 flex-shrink-0 min-w-0">
                      <div className="relative p-2 rounded-lg bg-muted/50 border border-border/50 group-hover:border-primary/20 transition-colors flex-shrink-0">
                        {React.createElement(currentFeature.icon, { className: "h-4 w-4 sm:h-5 sm:w-5 text-foreground" })}
                        {currentFeature.id === "council" && (
                          <Sparkles className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 text-primary animate-pulse" />
                        )}
                        {currentFeature.id === "forward" && (
                          <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 min-w-0">
                        <h3 className="text-sm sm:text-base font-semibold text-foreground whitespace-nowrap">
                          {currentFeature.title}
                        </h3>
                        {currentFeature.badge && (
                          <Badge 
                            variant="secondary" 
                            className={cn("text-[10px] px-1.5 py-0 h-4 font-semibold flex-shrink-0", currentFeature.badgeColor)}
                          >
                            {currentFeature.badge}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Description - Center (fills space) */}
                    <div className="flex-1 min-w-0 hidden md:flex md:justify-center md:px-4">
                      <p className="text-xs sm:text-sm text-muted-foreground/90 leading-snug truncate max-w-2xl text-center">
                        {currentFeature.description}
                      </p>
                    </div>

                    {/* Explore CTA - Right */}
                    <div className="flex items-center gap-2 flex-shrink-0 ml-auto">
                      <span className="hidden lg:inline text-xs font-medium text-muted-foreground group-hover:text-primary transition-colors">
                        Explore
                      </span>
                      <div className="p-1.5 rounded-md bg-muted/50 border border-border/50 group-hover:border-primary/30 group-hover:bg-primary/5 transition-all">
                        <ArrowRight className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          </AnimatePresence>

          {/* Compact Navigation Arrows */}
          <div className="absolute inset-y-0 -left-2 -right-2 flex items-center justify-between pointer-events-none">
            <button
              onClick={(e) => {
                e.preventDefault();
                goToPrev();
              }}
              className="pointer-events-auto p-1.5 rounded-md bg-background/95 backdrop-blur-sm border border-border hover:bg-muted transition-all shadow-sm opacity-0 group-hover:opacity-100"
              aria-label="Previous"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={(e) => {
                e.preventDefault();
                goToNext();
              }}
              className="pointer-events-auto p-1.5 rounded-md bg-background/95 backdrop-blur-sm border border-border hover:bg-muted transition-all shadow-sm opacity-0 group-hover:opacity-100"
              aria-label="Next"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Minimal Dots Indicator */}
        <div className="flex items-center justify-center gap-1.5 px-4 pb-2 pt-0.5">
          {features.map((feature, index) => (
            <button
              key={feature.id}
              onClick={() => goToIndex(index)}
              className={cn(
                "h-1 rounded-full transition-all duration-300",
                index === currentIndex 
                  ? "w-6 bg-primary" 
                  : "w-1 bg-muted-foreground/30 hover:bg-muted-foreground/50"
              )}
              aria-label={`Go to ${feature.title}`}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

