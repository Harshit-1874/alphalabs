"use client";

import { useState, useEffect } from "react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useAgents } from "@/hooks/use-agents";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";

interface DeleteAgentDialogProps {
    agentId: string | null;
    agentName: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    isArchived?: boolean;
}

export function DeleteAgentDialog({
    agentId,
    agentName,
    open,
    onOpenChange,
    isArchived = false,
}: DeleteAgentDialogProps) {
    const { deleteAgent } = useAgents();
    const { toast } = useToast();
    const [isDeleting, setIsDeleting] = useState(false);
    const [permanentDelete, setPermanentDelete] = useState(isArchived); // Default to true for archived agents

    // Reset permanentDelete when dialog opens
    useEffect(() => {
        if (open) {
            setPermanentDelete(isArchived);
        }
    }, [open, isArchived]);

    const handleDelete = async () => {
        if (!agentId) return;

        setIsDeleting(true);
        try {
            await deleteAgent(agentId, !permanentDelete); // archive=true by default
            toast({
                title: permanentDelete ? "Agent deleted" : "Agent archived",
                description: permanentDelete
                    ? `${agentName} has been permanently deleted`
                    : `${agentName} has been archived`,
            });
            onOpenChange(false);
            setPermanentDelete(isArchived); // Reset to default based on archived status
        } catch (err) {
            toast({
                title: "Error",
                description: err instanceof Error ? err.message : "Failed to delete agent",
                variant: "destructive",
            });
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>
                        {isArchived ? "Permanently Delete" : "Delete"} {agentName}?
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                        {permanentDelete
                            ? "This will permanently delete the agent and all associated data. This action cannot be undone."
                            : "This will archive the agent. You can restore it later from archived agents."}
                    </AlertDialogDescription>
                </AlertDialogHeader>

                {!isArchived && (
                    <div className="flex items-center space-x-2 py-2">
                        <Checkbox
                            id="permanent-delete"
                            checked={permanentDelete}
                            onCheckedChange={(checked) => setPermanentDelete(checked as boolean)}
                        />
                        <Label
                            htmlFor="permanent-delete"
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                            Permanently delete (cannot be undone)
                        </Label>
                    </div>
                )}

                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {permanentDelete ? "Delete Permanently" : "Archive Agent"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
