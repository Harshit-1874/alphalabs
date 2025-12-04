"use client";

import { useApiClient } from "@/lib/api";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { NotificationItem } from "@/types";

interface NotificationListResponse {
  notifications: Array<{
    id: string;
    type: string;
    category: string;
    title: string;
    message: string;
    action_url?: string | null;
    session_id?: string | null;
    result_id?: string | null;
    is_read: boolean;
    created_at: string;
  }>;
  total: number;
  unread_count: number;
}

interface UnreadCountResponse {
  count: number;
}

const mapNotification = (item: NotificationListResponse["notifications"][number]): NotificationItem => ({
  id: item.id,
  type: (item.type as NotificationItem["type"]) ?? "info",
  category: item.category,
  title: item.title,
  message: item.message,
  actionUrl: item.action_url ?? undefined,
  sessionId: item.session_id ?? undefined,
  resultId: item.result_id ?? undefined,
  isRead: item.is_read,
  createdAt: new Date(item.created_at),
});

export function useNotifications() {
  const { get, post } = useApiClient();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await get<NotificationListResponse>("/api/notifications?limit=20");
      setNotifications(data.notifications.map(mapNotification));
      setTotal(data.total);
      setUnreadCount(data.unread_count);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load notifications";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [get]);

  useEffect(() => {
    void fetchNotifications();
    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      void fetchNotifications();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const markAllAsRead = useCallback(async () => {
      try {
        await post("/api/notifications/mark-all-read");
      await fetchNotifications();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to mark notifications as read";
      setError(message);
    }
  }, [fetchNotifications, post]);

  const markAsRead = useCallback(
    async (id: string) => {
      try {
        const updated = await post<NotificationListResponse["notifications"][number]>(
          `/api/notifications/${id}/read`
        );
        setNotifications((prev) =>
          prev.map((notification) =>
            notification.id === id ? mapNotification(updated) : notification
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update notification";
        setError(message);
      }
    },
    [post]
  );

  const refreshUnreadCount = useCallback(async () => {
    try {
      const result = await get<UnreadCountResponse>("/api/notifications/unread-count");
      setUnreadCount(result.count);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch unread count";
      setError(message);
    }
  }, [get]);

  return useMemo(
    () => ({
      notifications,
      total,
      unreadCount,
      isLoading,
      error,
      markAllAsRead,
      markAsRead,
      refresh: fetchNotifications,
      refreshUnreadCount,
    }),
    [
      notifications,
      total,
      unreadCount,
      isLoading,
      error,
      markAllAsRead,
      markAsRead,
      fetchNotifications,
      refreshUnreadCount,
    ]
  );
}

