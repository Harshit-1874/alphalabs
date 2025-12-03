"use client";

import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import { motion } from "motion/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { Badge } from "@/components/ui/badge";

const timezones = [
  { value: "UTC", label: "(UTC+00:00) UTC" },
  { value: "America/New_York", label: "(UTC-05:00) Eastern Time" },
  { value: "America/Los_Angeles", label: "(UTC-08:00) Pacific Time" },
  { value: "Europe/London", label: "(UTC+00:00) London" },
  { value: "Asia/Tokyo", label: "(UTC+09:00) Tokyo" },
  { value: "Asia/Kolkata", label: "(UTC+05:30) India" },
];

export default function ProfileSettingsPage() {
  const { user } = useUser();
  const [displayName, setDisplayName] = useState(
    user?.firstName && user?.lastName
      ? `${user.firstName} ${user.lastName}`
      : user?.username || ""
  );
  const [timezone, setTimezone] = useState("Asia/Kolkata");

  const initials = user?.firstName && user?.lastName
    ? `${user.firstName[0]}${user.lastName[0]}`
    : user?.emailAddresses[0]?.emailAddress.slice(0, 2).toUpperCase() || "U";

  const email = user?.emailAddresses[0]?.emailAddress || "";

  return (
    <motion.div 
      className="space-y-6"
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30, mass: 0.8 }}
    >
      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Profile Picture</CardTitle>
          <CardDescription>Your avatar appears on certificates and across the platform</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <Avatar className="h-20 w-20 border-2 border-border">
            <AvatarImage src={user?.imageUrl} />
            <AvatarFallback className="bg-[hsl(var(--brand-flame))] text-xl text-white">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-2">
            <Button variant="outline" size="sm">
              Change Photo
            </Button>
            <Button variant="ghost" size="sm" className="text-muted-foreground">
              Remove
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Display Name</CardTitle>
          <CardDescription>This is how your name appears on certificates</CardDescription>
        </CardHeader>
        <CardContent>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="max-w-md"
          />
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Email</CardTitle>
          <CardDescription>Managed by Clerk authentication</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Input value={email} disabled className="max-w-md" />
            <Badge variant="outline" className="text-[hsl(var(--accent-green))]">
              Verified
            </Badge>
          </div>
          <Button variant="link" className="mt-2 h-auto p-0 text-xs">
            Change Email
          </Button>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Timezone</CardTitle>
          <CardDescription>Used for displaying timestamps</CardDescription>
        </CardHeader>
        <CardContent>
          <AnimatedSelect value={timezone} onValueChange={setTimezone}>
            <AnimatedSelectTrigger className="max-w-md">
              <AnimatedSelectValue />
            </AnimatedSelectTrigger>
            <AnimatedSelectContent>
              {timezones.map((tz) => (
                <AnimatedSelectItem key={tz.value} value={tz.value}>
                  {tz.label}
                </AnimatedSelectItem>
              ))}
            </AnimatedSelectContent>
          </AnimatedSelect>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
          Save Changes
        </Button>
      </div>
    </motion.div>
  );
}

