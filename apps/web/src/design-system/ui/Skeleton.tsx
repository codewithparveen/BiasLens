import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-(--color-ink-200) dark:bg-(--color-ink-800)", className)} />;
}
