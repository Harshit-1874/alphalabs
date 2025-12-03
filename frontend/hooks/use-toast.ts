// Simple toast hook implementation
// This provides a basic toast notification system
import { useState, useCallback } from "react";

interface ToastOptions {
    title: string;
    description?: string;
    variant?: "default" | "destructive";
    duration?: number;
}

interface Toast extends ToastOptions {
    id: string;
}

export function useToast() {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const toast = useCallback((options: ToastOptions) => {
        const id = Math.random().toString(36).substring(7);
        const newToast = { ...options, id };

        setToasts((prev) => [...prev, newToast]);

        // Auto-dismiss after duration
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, options.duration || 3000);

        // For now, also log to console as fallback
        if (options.variant === "destructive") {
            console.error(`[Toast Error] ${options.title}: ${options.description || ""}`);
        } else {
            console.log(`[Toast] ${options.title}: ${options.description || ""}`);
        }

        return { id };
    }, []);

    const dismiss = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return {
        toast,
        toasts,
        dismiss,
    };
}
