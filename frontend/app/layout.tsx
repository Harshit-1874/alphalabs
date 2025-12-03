import type { Metadata } from "next";
import { Geist, Geist_Mono, Syne, JetBrains_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { UserSyncProvider } from "@/components/providers/user-sync-provider";
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

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
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
      <html lang="en" suppressHydrationWarning>
        <body className={`${geistSans.variable} ${geistMono.variable} ${syne.variable} ${jetbrainsMono.variable} bg-background`}>
          <ThemeProvider>
            <UserSyncProvider>
              {children}
              <Toaster richColors position="bottom-right" />
            </UserSyncProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
