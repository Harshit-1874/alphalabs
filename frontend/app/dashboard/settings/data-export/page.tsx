"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Download } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

export default function DataExportSettingsPage() {
  const [exportOptions, setExportOptions] = useState({
    agentConfigs: true,
    testResults: true,
    tradeHistory: false,
    reasoningTraces: false,
    accountSettings: false,
  });

  const selectedCount = Object.values(exportOptions).filter(Boolean).length;
  const estimatedSize = selectedCount * 0.8; // Mock calculation

  const handleSelectAll = () => {
    setExportOptions({
      agentConfigs: true,
      testResults: true,
      tradeHistory: true,
      reasoningTraces: true,
      accountSettings: true,
    });
  };

  const handleClearAll = () => {
    setExportOptions({
      agentConfigs: false,
      testResults: false,
      tradeHistory: false,
      reasoningTraces: false,
      accountSettings: false,
    });
  };

  return (
    <motion.div 
      className="space-y-6"
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
    >
      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Data Export</CardTitle>
          <CardDescription>
            Export your data at any time. We support full data portability.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Export Options</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="agentConfigs"
              checked={exportOptions.agentConfigs}
              onCheckedChange={(checked) =>
                setExportOptions({
                  ...exportOptions,
                  agentConfigs: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="agentConfigs" className="text-sm font-medium">
                Agent Configurations (JSON)
              </Label>
              <p className="text-xs text-muted-foreground">
                All agent settings, indicators, and prompts
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="testResults"
              checked={exportOptions.testResults}
              onCheckedChange={(checked) =>
                setExportOptions({
                  ...exportOptions,
                  testResults: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="testResults" className="text-sm font-medium">
                Test Results (CSV)
              </Label>
              <p className="text-xs text-muted-foreground">
                All backtest and forward test results
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="tradeHistory"
              checked={exportOptions.tradeHistory}
              onCheckedChange={(checked) =>
                setExportOptions({
                  ...exportOptions,
                  tradeHistory: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="tradeHistory" className="text-sm font-medium">
                Trade History (CSV)
              </Label>
              <p className="text-xs text-muted-foreground">
                Complete trade-by-trade history
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="reasoningTraces"
              checked={exportOptions.reasoningTraces}
              onCheckedChange={(checked) =>
                setExportOptions({
                  ...exportOptions,
                  reasoningTraces: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="reasoningTraces" className="text-sm font-medium">
                Reasoning Traces (JSON)
              </Label>
              <p className="text-xs text-muted-foreground">
                AI decision logs (large file)
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="accountSettings"
              checked={exportOptions.accountSettings}
              onCheckedChange={(checked) =>
                setExportOptions({
                  ...exportOptions,
                  accountSettings: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="accountSettings" className="text-sm font-medium">
                Account Settings (JSON)
              </Label>
              <p className="text-xs text-muted-foreground">
                Preferences and configurations
              </p>
            </div>
          </div>

          <div className="flex gap-2 pt-4">
            <Button variant="outline" size="sm" onClick={handleSelectAll}>
              Select All
            </Button>
            <Button variant="outline" size="sm" onClick={handleClearAll}>
              Clear All
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card/30 p-4">
        <div>
          <p className="text-sm text-muted-foreground">
            Estimated size: <span className="font-mono">~{estimatedSize.toFixed(1)} MB</span>
          </p>
          <p className="text-xs text-muted-foreground">
            {selectedCount} of 5 options selected
          </p>
        </div>
        <Button
          disabled={selectedCount === 0}
          className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Download className="h-4 w-4" />
          Export Selected Data
        </Button>
      </div>
    </motion.div>
  );
}

