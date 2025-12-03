"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

export default function RiskLimitsSettingsPage() {
  const [limits, setLimits] = useState({
    maxPositionSize: 50,
    maxLeverage: 5,
    maxLossPerTrade: 5,
    maxDailyLoss: 10,
    maxTotalDrawdown: 20,
  });

  return (
    <motion.div 
      className="space-y-6"
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
    >
      <Card className="border-[hsl(var(--accent-amber)/0.3)] bg-[hsl(var(--accent-amber)/0.05)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <AlertTriangle className="h-5 w-5 text-[hsl(var(--accent-amber))]" />
            Global Risk Limits
          </CardTitle>
          <CardDescription>
            These are global risk limits that apply to all tests. The AI cannot
            exceed these limits even if instructed to.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Position Limits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Max Position Size (% of capital)</Label>
              <span className="font-mono text-sm">{limits.maxPositionSize}%</span>
            </div>
            <Slider
              value={[limits.maxPositionSize]}
              onValueChange={([value]) =>
                setLimits({ ...limits, maxPositionSize: value })
              }
              min={10}
              max={100}
              step={5}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Max Leverage</Label>
              <span className="font-mono text-sm">{limits.maxLeverage}x</span>
            </div>
            <Slider
              value={[limits.maxLeverage]}
              onValueChange={([value]) =>
                setLimits({ ...limits, maxLeverage: value })
              }
              min={1}
              max={10}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1x</span>
              <span>10x</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Loss Limits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Max Loss Per Trade (%)</Label>
              <Input
                type="number"
                value={limits.maxLossPerTrade}
                onChange={(e) =>
                  setLimits({
                    ...limits,
                    maxLossPerTrade: parseInt(e.target.value) || 0,
                  })
                }
                className="font-mono"
                min={1}
                max={20}
              />
            </div>
            <div className="space-y-2">
              <Label>Max Daily Loss (%)</Label>
              <Input
                type="number"
                value={limits.maxDailyLoss}
                onChange={(e) =>
                  setLimits({
                    ...limits,
                    maxDailyLoss: parseInt(e.target.value) || 0,
                  })
                }
                className="font-mono"
                min={1}
                max={50}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Max Total Drawdown (%)</Label>
            <Input
              type="number"
              value={limits.maxTotalDrawdown}
              onChange={(e) =>
                setLimits({
                  ...limits,
                  maxTotalDrawdown: parseInt(e.target.value) || 0,
                })
              }
              className="max-w-xs font-mono"
              min={5}
              max={50}
            />
            <p className="text-xs text-muted-foreground">
              Auto-stop forward test if exceeded
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button variant="outline">Reset to Defaults</Button>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
          Save Risk Limits
        </Button>
      </div>
    </motion.div>
  );
}

