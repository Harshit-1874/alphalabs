"use client";

import {
  User,
  CreditCard,
  Key,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useUser, useClerk } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  AnimatedDropdown,
  AnimatedDropdownContent,
  AnimatedDropdownItem,
  AnimatedDropdownLabel,
  AnimatedDropdownSeparator,
  AnimatedDropdownTrigger,
} from "@/components/ui/animated-dropdown";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";

interface SidebarUserFooterProps {
  isCollapsed: boolean;
}

export function SidebarUserFooter({ isCollapsed }: SidebarUserFooterProps) {
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const router = useRouter();
  const isMobile = useIsMobile();

  if (!isLoaded) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border/50 bg-muted/30 p-2">
        <div className="h-9 w-9 animate-pulse rounded-full bg-muted" />
        {!isCollapsed && (
          <div className="flex flex-1 flex-col gap-1">
            <div className="h-3 w-24 animate-pulse rounded bg-muted" />
            <div className="h-2 w-16 animate-pulse rounded bg-muted" />
          </div>
        )}
      </div>
    );
  }

  const initials = user?.firstName && user?.lastName
    ? `${user.firstName[0]}${user.lastName[0]}`
    : user?.emailAddresses[0]?.emailAddress.slice(0, 2).toUpperCase() || "U";

  const displayName = user?.firstName
    ? `${user.firstName} ${user.lastName || ""}`
    : user?.emailAddresses[0]?.emailAddress || "User";

  const email = user?.emailAddresses[0]?.emailAddress || "";

  const handleSignOut = () => {
    signOut(() => router.push("/"));
  };

  return (
    <AnimatedDropdown>
      <AnimatedDropdownTrigger asChild>
        <button
          className={cn(
            "flex w-full items-center gap-3 rounded-lg border border-border/50 bg-muted/30 p-2 transition-colors hover:bg-muted/50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
            isCollapsed && "justify-center p-2"
          )}
        >
          <Avatar className="h-9 w-9 border border-border/50">
            <AvatarImage src={user?.imageUrl} alt={displayName} />
            <AvatarFallback className="bg-[hsl(var(--brand-flame))] text-xs font-medium text-white">
              {initials}
            </AvatarFallback>
          </Avatar>

          {!isCollapsed && (
            <>
              <div className="flex flex-1 flex-col items-start text-left">
                <span className="max-w-[140px] truncate text-sm font-medium text-foreground">
                  {displayName}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  Pro Plan
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </>
          )}
        </button>
      </AnimatedDropdownTrigger>

      <AnimatedDropdownContent
        align={isMobile ? "center" : "end"}
        side={isMobile ? "top" : isCollapsed ? "right" : "bottom"}
        className="w-56"
        sideOffset={8}
      >
        <AnimatedDropdownLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{displayName}</p>
            <p className="text-xs leading-none text-muted-foreground">
              {email}
            </p>
          </div>
        </AnimatedDropdownLabel>
        <AnimatedDropdownSeparator />
        <AnimatedDropdownItem onSelect={() => router.push("/dashboard/settings")}>
          <User className="mr-2 h-4 w-4" />
          Profile
        </AnimatedDropdownItem>
        <AnimatedDropdownItem onSelect={() => router.push("/dashboard/settings")}>
          <CreditCard className="mr-2 h-4 w-4" />
          Billing
        </AnimatedDropdownItem>
        <AnimatedDropdownItem onSelect={() => router.push("/dashboard/settings/api-keys")}>
          <Key className="mr-2 h-4 w-4" />
          API Keys
        </AnimatedDropdownItem>
        <AnimatedDropdownSeparator />
        <AnimatedDropdownItem
          onSelect={handleSignOut}
          destructive
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </AnimatedDropdownItem>
      </AnimatedDropdownContent>
    </AnimatedDropdown>
  );
}

