import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        secondary:
          "border-border/50 bg-secondary/80 text-secondary-foreground hover:bg-secondary",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border-border text-foreground hover:bg-muted/50",
        success:
          "border-transparent bg-[hsl(var(--accent-profit))] text-white shadow-sm",
        warning:
          "border-transparent bg-[hsl(var(--accent-amber))] text-black shadow-sm",
        info:
          "border-transparent bg-[hsl(var(--accent-blue))] text-white shadow-sm",
        premium:
          "border-transparent bg-[hsl(var(--brand-flame))] text-white shadow-sm",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
