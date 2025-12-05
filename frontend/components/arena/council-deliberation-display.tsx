"use client";

import { useState } from "react";
import { Brain, ChevronDown, ChevronUp, Trophy, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { CouncilDeliberation } from "@/types/arena";

interface CouncilDeliberationDisplayProps {
  deliberation: CouncilDeliberation;
  className?: string;
}

export function CouncilDeliberationDisplay({
  deliberation,
  className,
}: CouncilDeliberationDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!deliberation || !deliberation.stage1 || deliberation.stage1.length === 0) {
    return null;
  }

  const getModelShortName = (modelId: string) => {
    const parts = modelId.split("/");
    const name = parts[1] || modelId;
    return name.split(":")[0].split("-").slice(0, 2).join("-");
  };

  const getModelColor = (index: number) => {
    const colors = [
      "bg-purple-500/10 text-purple-400 border-purple-500/20",
      "bg-blue-500/10 text-blue-400 border-blue-500/20",
      "bg-green-500/10 text-green-400 border-green-500/20",
      "bg-amber-500/10 text-amber-400 border-amber-500/20",
      "bg-pink-500/10 text-pink-400 border-pink-500/20",
    ];
    return colors[index % colors.length];
  };

  return (
    <Card className={cn("border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-blue-500/5", className)}>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Brain className="h-4 w-4 text-purple-400" />
            Council Deliberation
            <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4 bg-purple-500/20 text-purple-400 border-purple-500/30">
              {deliberation.stage1.length} MODELS
            </Badge>
          </CardTitle>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="px-4 pb-4 pt-0">
          <Tabs defaultValue="final" className="w-full">
            <TabsList className="grid w-full grid-cols-3 h-8">
              <TabsTrigger value="final" className="text-xs">Final</TabsTrigger>
              <TabsTrigger value="stage1" className="text-xs">Responses</TabsTrigger>
              <TabsTrigger value="rankings" className="text-xs">Rankings</TabsTrigger>
            </TabsList>

            {/* Final Decision (Stage 3) */}
            <TabsContent value="final" className="space-y-2 mt-3">
              <div className="flex items-center gap-2 mb-2">
                <Trophy className="h-4 w-4 text-amber-400" />
                <span className="text-xs font-semibold">Chairman's Synthesis</span>
                <Badge variant="secondary" className="text-[9px] px-2 py-0 bg-amber-500/10 text-amber-400 border-amber-500/20">
                  {getModelShortName(deliberation.stage3.model)}
                </Badge>
              </div>
              <ScrollArea className="h-[200px] rounded-md border border-border/50 bg-muted/20 p-3">
                <p className="text-xs leading-relaxed whitespace-pre-wrap">
                  {deliberation.stage3.response}
                </p>
              </ScrollArea>
            </TabsContent>

            {/* Individual Responses (Stage 1) */}
            <TabsContent value="stage1" className="space-y-2 mt-3">
              <p className="text-xs text-muted-foreground mb-2">
                Each model independently analyzed the market:
              </p>
              <ScrollArea className="h-[200px] space-y-3">
                {deliberation.stage1.map((response, idx) => (
                  <div key={idx} className="mb-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <Badge variant="secondary" className={cn("text-[9px] px-2 py-0.5", getModelColor(idx))}>
                        {getModelShortName(response.model)}
                      </Badge>
                    </div>
                    <div className="rounded-md border border-border/50 bg-muted/10 p-2.5">
                      <p className="text-xs leading-relaxed">
                        {response.response.length > 300
                          ? response.response.substring(0, 300) + "..."
                          : response.response}
                      </p>
                    </div>
                  </div>
                ))}
              </ScrollArea>
            </TabsContent>

            {/* Rankings (Stage 2) */}
            <TabsContent value="rankings" className="space-y-2 mt-3">
              <p className="text-xs text-muted-foreground mb-2">
                Models ranked each other's decisions:
              </p>
              
              {/* Aggregate Rankings */}
              {deliberation.aggregate_rankings && deliberation.aggregate_rankings.length > 0 && (
                <div className="rounded-md border border-border/50 bg-muted/10 p-3 mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs font-semibold">Aggregate Rankings</span>
                  </div>
                  <div className="space-y-1.5">
                    {deliberation.aggregate_rankings.map((ranking, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-muted-foreground w-4">
                            #{idx + 1}
                          </span>
                          <Badge variant="secondary" className={cn("text-[9px] px-2 py-0.5", getModelColor(idx))}>
                            {getModelShortName(ranking.model)}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          Avg: {ranking.average_rank.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Individual Rankings */}
              <ScrollArea className="h-[150px] space-y-2">
                {deliberation.stage2 && deliberation.stage2.map((ranking, idx) => (
                  <div key={idx} className="mb-2">
                    <Badge variant="secondary" className={cn("text-[9px] px-2 py-0.5 mb-1.5", getModelColor(idx))}>
                      {getModelShortName(ranking.model)}'s ranking
                    </Badge>
                    <div className="rounded-md border border-border/50 bg-muted/10 p-2">
                      <p className="text-[10px] leading-relaxed text-muted-foreground">
                        {ranking.ranking.length > 200
                          ? ranking.ranking.substring(0, 200) + "..."
                          : ranking.ranking}
                      </p>
                    </div>
                  </div>
                ))}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      )}
    </Card>
  );
}

