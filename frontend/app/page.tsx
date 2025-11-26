'use client';

import { Component as EtherealShadow } from "@/components/etheral-shadow";
import { Banner } from "@/components/banner";
import { BentoGrid } from "@/components/bento-grid";

export default function Home() {
  return (
    <main className="relative w-full min-h-screen overflow-hidden bg-black">
      {/* Ethereal Shadow Background */}
      <div className="fixed inset-0 z-0">
        <EtherealShadow
          color="rgba(128, 128, 128, 1)"
          animation={{ scale: 50, speed: 30 }}
          noise={{ opacity: 0.5, scale: 1.5 }}
          sizing="fill"
        />
      </div>

      {/* Content */}
      <div className="relative z-10 p-4 md:p-6 lg:p-8 space-y-4 md:space-y-6 lg:space-y-8">
        <Banner />
        <BentoGrid />
      </div>
    </main>
  );
}
