"use client";

import { useRef, useState } from "react";
import { Download, Share2, Award, TrendingUp, Calendar, Bot, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import type { TestResult } from "@/types/result";

interface CertificatePreviewProps {
  result: TestResult;
  agentName: string;
}

export function CertificatePreview({ result, agentName }: CertificatePreviewProps) {
  const certificateRef = useRef<HTMLDivElement>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const handleDownloadPDF = async () => {
    setIsGenerating(true);
    try {
      // Dynamic import to avoid SSR issues
      const html2canvas = (await import("html2canvas")).default;
      const jsPDF = (await import("jspdf")).default;

      if (!certificateRef.current) return;

      const canvas = await html2canvas(certificateRef.current, {
        scale: 2,
        backgroundColor: "#0A0A0F",
        logging: false,
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "landscape",
        unit: "px",
        format: [canvas.width, canvas.height],
      });

      pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
      pdf.save(`AlphaLab-Certificate-${result.id}.pdf`);
      
      toast.success("Certificate downloaded!");
    } catch (error) {
      console.error("PDF generation failed:", error);
      toast.error("Failed to generate PDF. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleShare = async () => {
    const shareData = {
      title: `AlphaLab Certificate - ${agentName}`,
      text: `My AI trading agent "${agentName}" achieved ${result.pnl >= 0 ? "+" : ""}${result.pnl.toFixed(2)}% return on AlphaLab! 🚀`,
      url: window.location.href,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        // User cancelled or share failed
        copyToClipboard();
      }
    } else {
      copyToClipboard();
    }
  };

  const copyToClipboard = () => {
    const text = `My AI trading agent "${agentName}" achieved ${result.pnl >= 0 ? "+" : ""}${result.pnl.toFixed(2)}% return on AlphaLab! 🚀 ${window.location.href}`;
    navigator.clipboard.writeText(text);
    toast.success("Link copied to clipboard!");
  };

  const isProfitable = result.pnl >= 0;

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        <Button variant="outline" onClick={handleShare} className="gap-2">
          <Share2 className="h-4 w-4" />
          Share
        </Button>
        <Button
          onClick={handleDownloadPDF}
          disabled={isGenerating}
          className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              Download PDF
            </>
          )}
        </Button>
      </div>

      {/* Certificate Preview */}
      <Card className="overflow-hidden border-2 border-primary/30">
        <div
          ref={certificateRef}
          className="relative bg-gradient-to-br from-[#0A0A0F] via-[#12121A] to-[#0A0A0F] p-8 md:p-12"
        >
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-5">
            <div className="absolute inset-0" style={{
              backgroundImage: `radial-gradient(circle at 25px 25px, white 1px, transparent 0)`,
              backgroundSize: "50px 50px",
            }} />
          </div>

          {/* Border Decoration */}
          <div className="absolute inset-4 border border-primary/20 rounded-lg pointer-events-none" />
          <div className="absolute inset-6 border border-primary/10 rounded-lg pointer-events-none" />

          {/* Content */}
          <div className="relative z-10 text-center">
            {/* Logo/Brand */}
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-2">
                <Award className="h-5 w-5 text-primary" />
                <span className="font-mono text-sm font-medium text-primary">
                  ALPHALAB
                </span>
              </div>
            </div>

            {/* Title */}
            <h1 className="mb-2 font-mono text-3xl font-bold tracking-tight text-white md:text-4xl">
              Certificate of Achievement
            </h1>
            <p className="mb-8 text-muted-foreground">
              This certifies that the AI trading agent
            </p>

            {/* Agent Name */}
            <div className="mb-8">
              <div className="inline-flex items-center gap-3 rounded-lg border border-border/50 bg-card/30 px-6 py-4">
                <Bot className="h-8 w-8 text-[hsl(var(--brand-flame))]" />
                <span className="font-mono text-2xl font-bold text-white">{agentName}</span>
              </div>
            </div>

            {/* Achievement */}
            <p className="mb-4 text-muted-foreground">
              has successfully completed a {result.type === "backtest" ? "backtest" : "forward test"} with
            </p>

            {/* PnL Display */}
            <div className="mb-8">
              <div className={`inline-flex items-center gap-3 rounded-xl px-8 py-4 ${
                isProfitable 
                  ? "bg-[hsl(var(--accent-profit)/0.1)] border border-[hsl(var(--accent-profit)/0.3)]" 
                  : "bg-[hsl(var(--accent-red)/0.1)] border border-[hsl(var(--accent-red)/0.3)]"
              }`}>
                <TrendingUp className={`h-8 w-8 ${isProfitable ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))] rotate-180"}`} />
                <span className={`font-mono text-4xl font-bold ${isProfitable ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"}`}>
                  {isProfitable ? "+" : ""}{result.pnl.toFixed(2)}%
                </span>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="mb-8 grid grid-cols-3 gap-4 max-w-md mx-auto">
              <div className="rounded-lg bg-card/30 p-3">
                <p className="text-xs text-muted-foreground">Win Rate</p>
                <p className="font-mono text-lg font-semibold text-white">{result.winRate}%</p>
              </div>
              <div className="rounded-lg bg-card/30 p-3">
                <p className="text-xs text-muted-foreground">Trades</p>
                <p className="font-mono text-lg font-semibold text-white">{result.totalTrades}</p>
              </div>
              <div className="rounded-lg bg-card/30 p-3">
                <p className="text-xs text-muted-foreground">Max DD</p>
                <p className="font-mono text-lg font-semibold text-[hsl(var(--accent-red))]">{result.maxDrawdown}%</p>
              </div>
            </div>

            {/* Date & Verification */}
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Issued on {formatDate(result.completedAt)}</span>
            </div>

            {/* Certificate ID */}
            <div className="mt-4">
              <Badge variant="outline" className="font-mono text-xs">
                Certificate ID: {result.id.toUpperCase()}
              </Badge>
            </div>

            {/* Verification QR Placeholder */}
            <div className="mt-6 flex justify-center">
              <div className="rounded-lg border border-border/50 bg-white p-2">
                <div className="h-16 w-16 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij48cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiB4PSIwIiB5PSIwIiBmaWxsPSIjMDAwIi8+PHJlY3Qgd2lkdGg9IjQiIGhlaWdodD0iNCIgeD0iNCIgeT0iMCIgZmlsbD0iIzAwMCIvPjxyZWN0IHdpZHRoPSI0IiBoZWlnaHQ9IjQiIHg9IjgiIHk9IjAiIGZpbGw9IiMwMDAiLz48cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiB4PSIwIiB5PSI0IiBmaWxsPSIjMDAwIi8+PHJlY3Qgd2lkdGg9IjQiIGhlaWdodD0iNCIgeD0iOCIgeT0iNCIgZmlsbD0iIzAwMCIvPjxyZWN0IHdpZHRoPSI0IiBoZWlnaHQ9IjQiIHg9IjAiIHk9IjgiIGZpbGw9IiMwMDAiLz48cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiB4PSI0IiB5PSI4IiBmaWxsPSIjMDAwIi8+PHJlY3Qgd2lkdGg9IjQiIGhlaWdodD0iNCIgeD0iOCIgeT0iOCIgZmlsbD0iIzAwMCIvPjwvc3ZnPg==')] bg-contain" />
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">Scan to verify</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

