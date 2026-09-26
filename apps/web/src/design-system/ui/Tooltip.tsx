import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [open, setOpen] = React.useState(false);
  const id = React.useId();

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {React.cloneElement(children, { "aria-describedby": id } as React.HTMLAttributes<HTMLElement>)}
      {open && (
        <span
          role="tooltip"
          id={id}
          className={cn(
            "pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-64 -translate-x-1/2",
            "rounded-md bg-(--color-ink-900) px-3 py-2 text-xs text-(--color-ink-50) shadow-lg",
            "dark:bg-(--color-ink-100) dark:text-(--color-ink-900)",
            className,
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
