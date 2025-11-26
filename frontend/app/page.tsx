'use client';

import { Banner } from "@/components/banner";
import { BentoGrid } from "@/components/bento-grid";

export default function Home() {
  return (
    <main className="relative w-full min-h-screen overflow-hidden bg-black">
      {/* Content */}
      <div className="relative z-10 p-4 md:p-6 lg:p-8 space-y-4 md:space-y-6 lg:space-y-8">
        <Banner />
        <BentoGrid />
      </div>
    </main>
  );
}
