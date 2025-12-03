"use client";

import { useState } from "react";
import {
  Share2,
  Copy,
  Check,
  Twitter,
  Linkedin,
  MessageCircle,
  Send,
  Link as LinkIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AnimatedDropdown,
  AnimatedDropdownContent,
  AnimatedDropdownItem,
  AnimatedDropdownSeparator,
  AnimatedDropdownTrigger,
} from "@/components/ui/animated-dropdown";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import type { TestResult } from "@/types/result";

interface ShareResultProps {
  result: TestResult;
  agentName: string;
  variant?: "button" | "dropdown";
}

export function ShareResult({ result, agentName, variant = "button" }: ShareResultProps) {
  const [copied, setCopied] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  const shareUrl = typeof window !== "undefined" 
    ? `${window.location.origin}/dashboard/results/${result.id}`
    : "";

  const shareText = `My AI trading agent "${agentName}" achieved ${result.pnl >= 0 ? "+" : ""}${result.pnl.toFixed(2)}% return on AlphaLab! 🚀`;
  const hashtags = "AlphaLab,AITrading,QuantTrading";

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Link copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy link");
    }
  };

  const shareToTwitter = () => {
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}&hashtags=${hashtags}`;
    window.open(url, "_blank", "width=550,height=420");
  };

  const shareToLinkedIn = () => {
    const url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
    window.open(url, "_blank", "width=550,height=420");
  };

  const shareToTelegram = () => {
    const url = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;
    window.open(url, "_blank", "width=550,height=420");
  };

  const shareToWhatsApp = () => {
    const url = `https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`;
    window.open(url, "_blank");
  };

  const nativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `AlphaLab Result - ${agentName}`,
          text: shareText,
          url: shareUrl,
        });
      } catch (err) {
        // User cancelled
      }
    } else {
      setShowDialog(true);
    }
  };

  if (variant === "dropdown") {
    return (
      <AnimatedDropdown>
        <AnimatedDropdownTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <Share2 className="h-4 w-4" />
            Share
          </Button>
        </AnimatedDropdownTrigger>
        <AnimatedDropdownContent align="end" className="w-48">
          <AnimatedDropdownItem onSelect={shareToTwitter}>
            <Twitter className="mr-2 h-4 w-4" />
            Twitter / X
          </AnimatedDropdownItem>
          <AnimatedDropdownItem onSelect={shareToLinkedIn}>
            <Linkedin className="mr-2 h-4 w-4" />
            LinkedIn
          </AnimatedDropdownItem>
          <AnimatedDropdownItem onSelect={shareToTelegram}>
            <Send className="mr-2 h-4 w-4" />
            Telegram
          </AnimatedDropdownItem>
          <AnimatedDropdownItem onSelect={shareToWhatsApp}>
            <MessageCircle className="mr-2 h-4 w-4" />
            WhatsApp
          </AnimatedDropdownItem>
          <AnimatedDropdownSeparator />
          <AnimatedDropdownItem onSelect={copyLink}>
            {copied ? (
              <>
                <Check className="mr-2 h-4 w-4 text-[hsl(var(--accent-green))]" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                Copy Link
              </>
            )}
          </AnimatedDropdownItem>
        </AnimatedDropdownContent>
      </AnimatedDropdown>
    );
  }

  return (
    <Dialog open={showDialog} onOpenChange={setShowDialog}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2" onClick={nativeShare}>
          <Share2 className="h-4 w-4" />
          Share
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5 text-primary" />
            Share Result
          </DialogTitle>
          <DialogDescription>
            Share your trading result with the world
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Preview Card */}
          <div className="rounded-lg border border-border/50 bg-muted/20 p-4">
            <p className="text-sm">{shareText}</p>
            <p className="mt-2 text-xs text-muted-foreground truncate">{shareUrl}</p>
          </div>

          {/* Social Buttons */}
          <div className="grid grid-cols-4 gap-3">
            <Button
              variant="outline"
              className="flex flex-col gap-1 h-auto py-3"
              onClick={shareToTwitter}
            >
              <Twitter className="h-5 w-5" />
              <span className="text-xs">Twitter</span>
            </Button>
            <Button
              variant="outline"
              className="flex flex-col gap-1 h-auto py-3"
              onClick={shareToLinkedIn}
            >
              <Linkedin className="h-5 w-5" />
              <span className="text-xs">LinkedIn</span>
            </Button>
            <Button
              variant="outline"
              className="flex flex-col gap-1 h-auto py-3"
              onClick={shareToTelegram}
            >
              <Send className="h-5 w-5" />
              <span className="text-xs">Telegram</span>
            </Button>
            <Button
              variant="outline"
              className="flex flex-col gap-1 h-auto py-3"
              onClick={shareToWhatsApp}
            >
              <MessageCircle className="h-5 w-5" />
              <span className="text-xs">WhatsApp</span>
            </Button>
          </div>

          {/* Copy Link */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <LinkIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={shareUrl}
                readOnly
                className="pl-9 font-mono text-xs"
              />
            </div>
            <Button variant="outline" onClick={copyLink} className="shrink-0">
              {copied ? (
                <Check className="h-4 w-4 text-[hsl(var(--accent-green))]" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

