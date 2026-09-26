import * as React from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface CopySnippetProps {
  code: string;
  className?: string;
}

export function CopySnippet({ code, className }: CopySnippetProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = React.useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can be unavailable (insecure context, permissions) --
      // fail silently rather than throw in the UI.
    }
  }, [code]);

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-md border border-(--border)",
        "bg-(--color-ink-900) px-4 py-3 text-(--color-ink-50)",
        className,
      )}
    >
      <code className="font-(family-name:--font-mono) text-sm">{code}</code>
      <button
        type="button"
        onClick={handleCopy}
        aria-label="Copy to clipboard"
        className="shrink-0 rounded p-1.5 text-(--color-ink-300) hover:bg-(--color-ink-800) hover:text-(--color-ink-50)"
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  );
}
