"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

export default function NotificationsSettingsPage() {
  const [emailNotifications, setEmailNotifications] = useState({
    testCompleted: true,
    tradeExecuted: true,
    dailySummary: false,
    stopLossHit: true,
    marketing: false,
  });

  const [inAppNotifications, setInAppNotifications] = useState({
    showToasts: true,
    soundEffects: true,
    desktopNotifications: false,
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
          <CardTitle className="text-lg">Email Notifications</CardTitle>
          <CardDescription>Configure when you want to receive emails</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="testCompleted"
              checked={emailNotifications.testCompleted}
              onCheckedChange={(checked) =>
                setEmailNotifications({
                  ...emailNotifications,
                  testCompleted: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="testCompleted" className="text-sm font-medium">
                Test completed
              </Label>
              <p className="text-xs text-muted-foreground">
                When backtest or forward test finishes
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="tradeExecuted"
              checked={emailNotifications.tradeExecuted}
              onCheckedChange={(checked) =>
                setEmailNotifications({
                  ...emailNotifications,
                  tradeExecuted: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="tradeExecuted" className="text-sm font-medium">
                Trade executed
              </Label>
              <p className="text-xs text-muted-foreground">
                When forward test opens/closes position
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="dailySummary"
              checked={emailNotifications.dailySummary}
              onCheckedChange={(checked) =>
                setEmailNotifications({
                  ...emailNotifications,
                  dailySummary: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="dailySummary" className="text-sm font-medium">
                Daily summary
              </Label>
              <p className="text-xs text-muted-foreground">
                Daily recap of active sessions
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="stopLossHit"
              checked={emailNotifications.stopLossHit}
              onCheckedChange={(checked) =>
                setEmailNotifications({
                  ...emailNotifications,
                  stopLossHit: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="stopLossHit" className="text-sm font-medium">
                Stop loss hit
              </Label>
              <p className="text-xs text-muted-foreground">Immediate alert</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="marketing"
              checked={emailNotifications.marketing}
              onCheckedChange={(checked) =>
                setEmailNotifications({
                  ...emailNotifications,
                  marketing: checked as boolean,
                })
              }
            />
            <div>
              <Label htmlFor="marketing" className="text-sm font-medium">
                Marketing & product updates
              </Label>
              <p className="text-xs text-muted-foreground">
                News and feature announcements
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">In-App Notifications</CardTitle>
          <CardDescription>Configure notification behavior in the app</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="showToasts"
              checked={inAppNotifications.showToasts}
              onCheckedChange={(checked) =>
                setInAppNotifications({
                  ...inAppNotifications,
                  showToasts: checked as boolean,
                })
              }
            />
            <Label htmlFor="showToasts" className="text-sm">
              Show toast notifications
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="soundEffects"
              checked={inAppNotifications.soundEffects}
              onCheckedChange={(checked) =>
                setInAppNotifications({
                  ...inAppNotifications,
                  soundEffects: checked as boolean,
                })
              }
            />
            <Label htmlFor="soundEffects" className="text-sm">
              Sound effects
            </Label>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="desktopNotifications"
                checked={inAppNotifications.desktopNotifications}
                onCheckedChange={(checked) =>
                  setInAppNotifications({
                    ...inAppNotifications,
                    desktopNotifications: checked as boolean,
                  })
                }
              />
              <Label htmlFor="desktopNotifications" className="text-sm">
                Desktop notifications
              </Label>
            </div>
            <Button variant="outline" size="sm">
              Request Permission
            </Button>
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

