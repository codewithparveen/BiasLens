import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      tone: {
        neutral: "border-(--border) bg-(--bg-elevated) text-(--fg-muted)",
        low: "border-transparent bg-(--color-signal-low)/15 text-(--signal-low-text)",
        mid: "border-transparent bg-(--color-signal-mid)/15 text-(--signal-mid-text)",
        high: "border-transparent bg-(--color-signal-high)/15 text-(--signal-high-text)",
        accent: "border-transparent bg-(--accent)/15 text-(--accent)",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
