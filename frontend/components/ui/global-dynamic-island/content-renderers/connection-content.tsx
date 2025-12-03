"use client";

import { motion } from "motion/react";
import { Wifi, WifiOff, RefreshCw } from "lucide-react";
import { DynamicContainer } from "@/components/ui/dynamic-island";
import type { ConnectionData } from "@/lib/stores/dynamic-island-store";

interface ConnectionContentProps {
  data: ConnectionData;
}

export const ConnectionContent = ({ data }: ConnectionContentProps) => {
  const statusConfig = {
    connected: {
      icon: Wifi,
      text: "Connected",
      color: "hsl(var(--accent-profit))",
    },
    disconnected: {
      icon: WifiOff,
      text: "Disconnected",
      color: "hsl(var(--accent-red))",
    },
    reconnecting: {
      icon: RefreshCw,
      text: "Reconnecting...",
      color: "hsl(var(--accent-amber))",
    },
  };
  
  const config = statusConfig[data.status];
  const Icon = config.icon;
  
  return (
    <DynamicContainer className="flex h-full w-full items-center justify-center">
      <div className="flex items-center gap-2 px-4">
        <motion.div
          initial={{ scale: 0, rotate: data.status === "reconnecting" ? 0 : -90 }}
          animate={{ 
            scale: 1, 
            rotate: data.status === "reconnecting" ? 360 : 0,
          }}
          transition={
            data.status === "reconnecting" 
              ? { rotate: { duration: 1, repeat: Infinity, ease: "linear" }, scale: { type: "spring", stiffness: 500 } }
              : { type: "spring", stiffness: 500, damping: 20 }
          }
        >
          <Icon className="h-4 w-4" style={{ color: config.color }} />
        </motion.div>
        <motion.span 
          className="text-sm font-medium text-white"
          initial={{ opacity: 0, x: -5 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          {config.text}
        </motion.span>
        {data.status === "connected" && (
          <motion.div
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: config.color }}
            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </div>
    </DynamicContainer>
  );
};

