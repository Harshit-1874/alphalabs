"use client";

import { useState } from "react";
import { Key, Plus, Eye, EyeOff, RefreshCw, Edit, Trash2, ExternalLink, Check, AlertCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { useApiKeys, type ApiKeyCreate } from "@/hooks/use-api-keys";
import { useToast } from "@/hooks/use-toast";
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

export default function ApiKeysSettingsPage() {
  const { apiKeys, isLoading, error, createApiKey, validateApiKey, deleteApiKey, refetch } = useApiKeys();
  const { toast } = useToast();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreate>({
    provider: "openrouter",
    label: "",
    api_key: "",
    set_as_default: false
  });
  const [showKey, setShowKey] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [validatingKeyId, setValidatingKeyId] = useState<string | null>(null);
  const [deletingKeyId, setDeletingKeyId] = useState<string | null>(null);
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);

  const handleSaveApiKey = async () => {
    if (!newKey.api_key.trim()) {
      toast({
        title: "Error",
        description: "Please enter an API key",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      await createApiKey(newKey);
      toast({
        title: "Success",
        description: "API key saved successfully",
      });
      setShowAddDialog(false);
      setNewKey({ provider: "openrouter", label: "", api_key: "", set_as_default: false });
    } catch (err) {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to save API key",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleValidateKey = async (id: string) => {
    setValidatingKeyId(id);
    try {
      const result = await validateApiKey(id);
      if (result.valid) {
        toast({
          title: "Valid API Key",
          description: `Key is valid. ${result.models_available?.length || 0} models available.`,
        });
      } else {
        toast({
          title: "Invalid API Key",
          description: result.error || "The API key is invalid",
          variant: "destructive",
        });
      }
    } catch (err) {
      toast({
        title: "Validation Failed",
        description: err instanceof Error ? err.message : "Failed to validate API key",
        variant: "destructive",
      });
    } finally {
      setValidatingKeyId(null);
    }
  };

  const handleDeleteKey = async () => {
    if (!keyToDelete) return;

    setDeletingKeyId(keyToDelete);
    try {
      await deleteApiKey(keyToDelete);
      toast({
        title: "Success",
        description: "API key deleted successfully",
      });
      setKeyToDelete(null);
    } catch (err) {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to delete API key",
        variant: "destructive",
      });
    } finally {
      setDeletingKeyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">API Key Security</CardTitle>
          <CardDescription>
            Your API keys are encrypted and stored securely. We never have access to
            your actual keys - only encrypted versions.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Saved API Keys */}
      <Card className="border-border/50 bg-card/30">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">Saved API Keys</CardTitle>
            <CardDescription>Manage your stored API keys</CardDescription>
          </div>
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add New API Key
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add API Key</DialogTitle>
                <DialogDescription>
                  Add a new API key for your AI models
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select
                    value={newKey.provider}
                    onValueChange={(value) => setNewKey({ ...newKey, provider: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                      <SelectItem value="anthropic" disabled>
                        Anthropic (Coming soon)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Label (Optional)</Label>
                  <Input
                    placeholder="e.g., Work Account"
                    value={newKey.label}
                    onChange={(e) => setNewKey({ ...newKey, label: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">
                    A name to help you identify this key
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    placeholder="sk-or-v1-..."
                    value={newKey.api_key}
                    onChange={(e) => setNewKey({ ...newKey, api_key: e.target.value })}
                  />
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Get a key from OpenRouter
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="setDefault"
                    checked={newKey.set_as_default}
                    onCheckedChange={(checked) =>
                      setNewKey({ ...newKey, set_as_default: checked as boolean })
                    }
                  />
                  <Label htmlFor="setDefault" className="text-sm">
                    Set as default key for new agents
                  </Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowAddDialog(false)} disabled={isSaving}>
                  Cancel
                </Button>
                <Button onClick={handleSaveApiKey} disabled={isSaving}>
                  {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save API Key
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" size="sm" onClick={refetch} className="mt-2">
                Retry
              </Button>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/50 bg-muted/20 p-8 text-center">
              <Key className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <h3 className="mt-4 text-sm font-medium">No API keys yet</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Add your first API key to start using AI models
              </p>
            </div>
          ) : (
            apiKeys.map((apiKey) => (
              <div
                key={apiKey.id}
                className="rounded-lg border border-border/50 bg-muted/20 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{apiKey.provider}</span>
                      {apiKey.label && (
                        <span className="text-sm text-muted-foreground">({apiKey.label})</span>
                      )}
                      {apiKey.is_default && (
                        <Badge variant="secondary" className="text-xs">
                          Default
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
                      {apiKey.key_prefix}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Added: {new Date(apiKey.created_at).toLocaleDateString()} • Last used:{" "}
                      {apiKey.last_used_at ? new Date(apiKey.last_used_at).toLocaleDateString() : "Never"}
                    </p>
                    {apiKey.used_by && apiKey.used_by.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Used by: {apiKey.used_by.join(", ")}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs",
                        apiKey.status === "valid" &&
                        "border-[hsl(var(--accent-green)/0.3)] text-[hsl(var(--accent-green))]",
                        apiKey.status === "invalid" &&
                        "border-[hsl(var(--accent-red)/0.3)] text-[hsl(var(--accent-red))]",
                        apiKey.status === "untested" &&
                        "border-[hsl(var(--accent-amber)/0.3)] text-[hsl(var(--accent-amber))]"
                      )}
                    >
                      {apiKey.status === "valid" && <Check className="mr-1 h-3 w-3" />}
                      {apiKey.status === "untested" && <AlertCircle className="mr-1 h-3 w-3" />}
                      {apiKey.status.charAt(0).toUpperCase() + apiKey.status.slice(1)}
                    </Badge>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 border-t border-border/50 pt-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleValidateKey(apiKey.id)}
                    disabled={validatingKeyId === apiKey.id}
                  >
                    {validatingKeyId === apiKey.id ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    Test
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setKeyToDelete(apiKey.id)}
                    disabled={deletingKeyId === apiKey.id}
                  >
                    {deletingKeyId === apiKey.id ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Delete
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Supported Providers */}
      <Card className="border-border/50 bg-card/30">
        <CardHeader>
          <CardTitle className="text-lg">Supported Providers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border/50 bg-muted/10 p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">OpenRouter</span>
                <Badge variant="secondary" className="text-[hsl(var(--accent-green))]">
                  Active
                </Badge>
              </div>
            </div>
            <div className="rounded-lg border border-border/50 bg-muted/10 p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Direct API</span>
                <Button variant="link" size="sm" className="h-auto p-0">
                  Setup →
                </Button>
              </div>
            </div>
            <div className="rounded-lg border border-border/50 bg-muted/10 p-4 opacity-60">
              <div className="flex items-center justify-between">
                <span className="font-medium">Anthropic Direct</span>
                <span className="text-xs text-muted-foreground">Coming soon</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!keyToDelete} onOpenChange={() => setKeyToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete API Key?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this API key? This action cannot be undone.
              {keyToDelete && apiKeys.find(k => k.id === keyToDelete)?.used_by?.length! > 0 && (
                <span className="mt-2 block font-medium text-destructive">
                  Warning: This key is currently used by agents: {apiKeys.find(k => k.id === keyToDelete)?.used_by?.join(", ")}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteKey}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

