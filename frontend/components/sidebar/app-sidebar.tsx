"use client";

import * as React from "react";
import {
  LayoutDashboard,
  Bot,
  History,
  Play,
  BarChart3,
  Settings,
  Bell,
} from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover-radix";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SidebarLogo } from "./sidebar-logo";
import { SidebarUserFooter } from "./sidebar-user-footer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores";
import { DUMMY_NOTIFICATIONS } from "@/lib/dummy-data";
import { useIsMobile } from "@/hooks/use-mobile";

// Notification content shared between mobile and desktop
function NotificationList({ displayCount, markAllAsRead, notifications, isMobile = false }: {
  displayCount: number;
  markAllAsRead: () => void;
  notifications: typeof DUMMY_NOTIFICATIONS;
  isMobile?: boolean;
}) {
  return (
    <>
      <div className={cn(
        "flex items-center border-b border-border p-3",
        isMobile ? "justify-center pt-4" : "justify-between"
      )}>
        <h4 className="font-semibold">Notifications</h4>
        {displayCount > 0 && !isMobile && (
          <Button
            variant="ghost"
            size="sm"
            className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => markAllAsRead()}
          >
            Mark all read
          </Button>
        )}
      </div>
      {/* Mark all read button for mobile - below header */}
      {displayCount > 0 && isMobile && (
        <div className="flex justify-end px-3 py-2 border-b border-border/50">
          <Button
            variant="ghost"
            size="sm"
            className="h-auto py-1 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => markAllAsRead()}
          >
            Mark all read
          </Button>
        </div>
      )}
      <ScrollArea className="h-[400px] md:h-[300px]">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
            <Bell className="mb-2 h-8 w-8" />
            <p className="text-sm">No notifications</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {notifications.map((notification) => (
              <Link
                key={notification.id}
                href={notification.actionUrl || "#"}
                className={cn(
                  "block p-3 transition-colors hover:bg-muted/50",
                  !notification.read && "bg-muted/30"
                )}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                      notification.type === "success" && "bg-[hsl(var(--accent-profit))]",
                      notification.type === "error" && "bg-[hsl(var(--accent-red))]",
                      notification.type === "warning" && "bg-[hsl(var(--accent-amber))]",
                      notification.type === "info" && "bg-[hsl(var(--accent-blue))]"
                    )}
                  />
                  <div className="flex-1 min-w-0 space-y-1">
                    <p className="text-sm font-medium leading-none truncate">
                      {notification.title}
                    </p>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {notification.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </ScrollArea>
    </>
  );
}

// Notification Bell Component - uses Sheet on mobile, Popover on desktop
function NotificationBell({ isCollapsed }: { isCollapsed: boolean }) {
  const { unreadCount, markAllAsRead } = useUIStore();
  const isMobile = useIsMobile();
  const notifications = DUMMY_NOTIFICATIONS;
  const displayCount = unreadCount || notifications.filter((n) => !n.read).length;

  const triggerButton = (
    <SidebarMenuButton tooltip="Notifications" className="relative">
      <Bell className="h-4 w-4" />
      <span>Notifications</span>
      {displayCount > 0 && (
        <span
          className={cn(
            "absolute flex h-5 w-5 items-center justify-center rounded-full bg-[hsl(var(--accent-red))] text-[10px] font-bold text-white",
            isCollapsed ? "right-1 top-1" : "right-2 top-1/2 -translate-y-1/2"
          )}
        >
          {displayCount > 9 ? "9+" : displayCount}
        </span>
      )}
    </SidebarMenuButton>
  );

  // Mobile: use Sheet (drawer)
  if (isMobile) {
    return (
      <Sheet>
        <SheetTrigger asChild>
          {triggerButton}
        </SheetTrigger>
        <SheetContent side="bottom" className="h-[85vh] p-0 rounded-t-xl">
          <SheetHeader className="sr-only">
            <SheetTitle>Notifications</SheetTitle>
          </SheetHeader>
          <NotificationList
            displayCount={displayCount}
            markAllAsRead={markAllAsRead}
            notifications={notifications}
            isMobile={true}
          />
        </SheetContent>
      </Sheet>
    );
  }

  // Desktop: use Popover
  return (
    <Popover>
      <PopoverTrigger asChild>
        {triggerButton}
      </PopoverTrigger>
      <PopoverContent
        side="right"
        align="end"
        className="w-80 p-0"
        sideOffset={8}
      >
        <NotificationList
          displayCount={displayCount}
          markAllAsRead={markAllAsRead}
          notifications={notifications}
        />
      </PopoverContent>
    </Popover>
  );
}

// Navigation items configuration
const mainNavItems = [
  {
    title: "Dashboard",
    url: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "My Agents",
    url: "/dashboard/agents",
    icon: Bot,
    badge: "3", // This would come from state/API
  },
];

const arenaNavItems = [
  {
    title: "Backtest",
    url: "/dashboard/arena/backtest",
    icon: History,
  },
  {
    title: "Forward Test",
    url: "/dashboard/arena/forward",
    icon: Play,
    badge: "LIVE", // This would be conditional based on active sessions
    badgeVariant: "live" as const,
  },
];

const recordsNavItems = [
  {
    title: "Results & Certs",
    url: "/dashboard/results",
    icon: BarChart3,
  },
];

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";

  const isActive = (url: string) => {
    if (url === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(url);
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarLogo isCollapsed={isCollapsed} />
      </SidebarHeader>

      <SidebarContent>
        {/* Main Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Main</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                  {item.badge && !isCollapsed && (
                    <SidebarMenuBadge className="bg-muted text-muted-foreground">
                      {item.badge}
                    </SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Arena Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Arena</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {arenaNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                  {item.badge && !isCollapsed && (
                    <SidebarMenuBadge
                      className={cn(
                        item.badgeVariant === "live"
                          ? "bg-[hsl(var(--accent-profit)/0.15)] text-[hsl(var(--accent-profit))] animate-pulse-live"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {item.badge}
                    </SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Records Navigation */}
        <SidebarGroup>
          <SidebarGroupLabel>Records</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {recordsNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.url)}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Bottom Actions */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {/* Notifications */}
              <SidebarMenuItem>
                <NotificationBell isCollapsed={isCollapsed} />
              </SidebarMenuItem>

              {/* Settings */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive("/dashboard/settings")}
                  tooltip="Settings"
                >
                  <Link href="/dashboard/settings">
                    <Settings className="h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarUserFooter isCollapsed={isCollapsed} />
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}

