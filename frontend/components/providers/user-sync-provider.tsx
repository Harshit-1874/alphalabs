"use client";

import { useEffect, useRef } from "react";
import { useUser } from "@clerk/nextjs";
import { useApi } from "@/lib/api";

export function UserSyncProvider({ children }: { children: React.ReactNode }) {
    const { user, isLoaded } = useUser();
    const { request } = useApi();
    const syncedRef = useRef(false);

    useEffect(() => {
        const syncUser = async () => {
            if (isLoaded && user && !syncedRef.current) {
                try {
                    await request("/api/users/sync", { method: "POST" });
                    syncedRef.current = true;
                    console.log("User synced successfully");
                } catch (error) {
                    console.error("Failed to sync user:", error);
                }
            }
        };

        syncUser();
    }, [isLoaded, user, request]);

    return <>{children}</>;
}
