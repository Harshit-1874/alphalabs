import type { Metadata } from "next";
import { Geist, Geist_Mono, Syne } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const syne = Syne({
  variable: "--font-syne",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AlphaLab — The Wind Tunnel for Trading AIs",
  description: "Verify an AI trading agent's skill with repeatable historical simulations and an auditable Certificate of Intelligence. No-code sandbox, BYO model key, verifiable results.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <body className={`${geistSans.variable} ${geistMono.variable} ${syne.variable} bg-black`}>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
