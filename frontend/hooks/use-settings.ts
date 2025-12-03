import { useState, useEffect, useCallback } from "react";
import { useApi } from "@/lib/api";
import { useUser as useClerkUser } from "@clerk/nextjs";
import { toast } from "sonner";

export interface UserSettings {
    theme: string;
    accent_color: string;
    sidebar_collapsed: boolean;
    chart_grid_lines: boolean;
    chart_crosshair: boolean;
    email_notifications: {
        test_completed: boolean;
        trade_executed: boolean;
        daily_summary: boolean;
        stop_loss_hit: boolean;
        marketing: boolean;
    };
    inapp_notifications: {
        show_toasts: boolean;
        sound_effects: boolean;
        desktop_notifications: boolean;
    };
    default_asset: string;
    default_timeframe: string;
    default_capital: number;
    default_playback_speed: string;
    safety_mode_default: boolean;
    allow_leverage_default: boolean;
    max_position_size_pct: number;
    max_leverage: number;
    max_loss_per_trade_pct: number;
    max_daily_loss_pct: number;
    max_total_drawdown_pct: number;
}

export function useSettings() {
    const { request } = useApi();
    const { user: clerkUser, isLoaded: isClerkLoaded } = useClerkUser();
    const [settings, setSettings] = useState<UserSettings | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const fetchSettings = useCallback(async () => {
        if (!isClerkLoaded || !clerkUser) {
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            const data = await request<{ settings: UserSettings }>("/api/users/me/settings");
            setSettings(data.settings);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch settings:", err);
            setError(err instanceof Error ? err : new Error("Unknown error"));
        } finally {
            setIsLoading(false);
        }
    }, [request, isClerkLoaded, clerkUser]);

    const updateSettings = async (newSettings: Partial<UserSettings>) => {
        try {
            setIsSaving(true);
            const data = await request<{ settings: UserSettings }>("/api/users/me/settings", {
                method: "PUT",
                body: newSettings,
            });
            setSettings(data.settings);
            toast.success("Settings saved successfully");
            return data.settings;
        } catch (err) {
            console.error("Failed to update settings:", err);
            toast.error("Failed to save settings");
            throw err;
        } finally {
            setIsSaving(false);
        }
    };

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    return { settings, isLoading, isSaving, error, updateSettings, refetch: fetchSettings };
}
