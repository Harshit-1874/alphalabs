import { useState, useEffect, useCallback } from "react";
import { useApi } from "@/lib/api";
import { useUser as useClerkUser } from "@clerk/nextjs";

export interface UserProfile {
    id: string;
    clerk_id: string;
    email: string;
    first_name: string;
    last_name: string;
    username: string;
    image_url: string;
    timezone: string;
    plan: string;
    created_at: string;
}

export function useUserProfile() {
    const { request } = useApi();
    const { user: clerkUser, isLoaded: isClerkLoaded } = useClerkUser();
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    const fetchUserProfile = useCallback(async () => {
        if (!isClerkLoaded || !clerkUser) {
            setIsLoading(false);
            return;
        }

        try {
            setIsLoading(true);
            const data = await request<{ user: UserProfile }>("/api/users/me");
            setUserProfile(data.user);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch user profile:", err);
            setError(err instanceof Error ? err : new Error("Unknown error"));
        } finally {
            setIsLoading(false);
        }
    }, [request, isClerkLoaded, clerkUser]);

    const updateUserProfile = async (updates: Partial<UserProfile>) => {
        try {
            const data = await request<{ user: UserProfile }>("/api/users/me", {
                method: "PUT",
                body: updates,
            });
            setUserProfile(data.user);
            return data.user;
        } catch (err) {
            console.error("Failed to update user profile:", err);
            throw err;
        }
    };

    useEffect(() => {
        fetchUserProfile();
    }, [fetchUserProfile]);

    return { userProfile, isLoading, error, updateUserProfile, refetch: fetchUserProfile };
}
