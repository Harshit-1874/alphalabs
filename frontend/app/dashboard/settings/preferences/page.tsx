"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";

export default function PreferencesSettingsPage() {
  const [preferences, setPreferences] = useState({
    defaultAsset: "btc-usdt",
    defaultTimeframe: "1h",
    defaultCapital: "10000",
    defaultSpeed: "normal",
    safetyModeDefault: true,
    allowLeverageDefault: false,
  });

  return (
    <motion.div 
      className="space-y-6"
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
    >
      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Default Settings</CardTitle>
          <CardDescription>
            These settings will be used as defaults when creating new tests.
            You can override them in individual test configurations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Default Asset</Label>
              <AnimatedSelect
                value={preferences.defaultAsset}
                onValueChange={(value) =>
                  setPreferences({ ...preferences, defaultAsset: value })
                }
              >
                <AnimatedSelectTrigger>
                  <AnimatedSelectValue />
                </AnimatedSelectTrigger>
                <AnimatedSelectContent>
                  <AnimatedSelectItem value="btc-usdt">BTC/USDT</AnimatedSelectItem>
                  <AnimatedSelectItem value="eth-usdt">ETH/USDT</AnimatedSelectItem>
                  <AnimatedSelectItem value="sol-usdt">SOL/USDT</AnimatedSelectItem>
                </AnimatedSelectContent>
              </AnimatedSelect>
            </div>
            <div className="space-y-2">
              <Label>Default Timeframe</Label>
              <AnimatedSelect
                value={preferences.defaultTimeframe}
                onValueChange={(value) =>
                  setPreferences({ ...preferences, defaultTimeframe: value })
                }
              >
                <AnimatedSelectTrigger>
                  <AnimatedSelectValue />
                </AnimatedSelectTrigger>
                <AnimatedSelectContent>
                  <AnimatedSelectItem value="15m">15 Minutes</AnimatedSelectItem>
                  <AnimatedSelectItem value="1h">1 Hour</AnimatedSelectItem>
                  <AnimatedSelectItem value="4h">4 Hours</AnimatedSelectItem>
                  <AnimatedSelectItem value="1d">1 Day</AnimatedSelectItem>
                </AnimatedSelectContent>
              </AnimatedSelect>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Default Starting Capital</Label>
            <Input
              type="number"
              value={preferences.defaultCapital}
              onChange={(e) =>
                setPreferences({ ...preferences, defaultCapital: e.target.value })
              }
              className="max-w-xs font-mono"
            />
          </div>

          <div className="space-y-2">
            <Label>Default Playback Speed (Backtest)</Label>
            <AnimatedSelect
              value={preferences.defaultSpeed}
              onValueChange={(value) =>
                setPreferences({ ...preferences, defaultSpeed: value })
              }
            >
              <AnimatedSelectTrigger className="max-w-xs">
                <AnimatedSelectValue />
              </AnimatedSelectTrigger>
              <AnimatedSelectContent>
                <AnimatedSelectItem value="slow">Slow (1s/candle)</AnimatedSelectItem>
                <AnimatedSelectItem value="normal">Normal (500ms/candle)</AnimatedSelectItem>
                <AnimatedSelectItem value="fast">Fast (200ms/candle)</AnimatedSelectItem>
                <AnimatedSelectItem value="instant">Instant</AnimatedSelectItem>
              </AnimatedSelectContent>
            </AnimatedSelect>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Safety Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="safetyMode"
              checked={preferences.safetyModeDefault}
              onCheckedChange={(checked) =>
                setPreferences({
                  ...preferences,
                  safetyModeDefault: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="safetyMode" className="text-sm font-medium">
                Enable Safety Mode by default
              </Label>
              <p className="text-xs text-muted-foreground">
                Auto stop-loss at -2% per trade
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="leverage"
              checked={preferences.allowLeverageDefault}
              onCheckedChange={(checked) =>
                setPreferences({
                  ...preferences,
                  allowLeverageDefault: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="leverage" className="text-sm font-medium">
                Allow Leverage by default
              </Label>
              <p className="text-xs text-muted-foreground">Up to 5x leverage</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
          Save Preferences
        </Button>
      </div>
    </motion.div>
  );
}

