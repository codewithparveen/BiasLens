import { cn } from "@/lib/utils";

interface TabsProps {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div role="tablist" className={cn("flex gap-1 border-b border-(--border)", className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative px-4 py-2 text-sm font-medium transition-colors",
              isActive ? "text-(--accent)" : "text-(--fg-muted) hover:text-(--fg)",
            )}
          >
            {tab.label}
            {isActive && <span className="absolute inset-x-0 -bottom-px h-0.5 bg-(--accent)" />}
          </button>
        );
      })}
    </div>
  );
}
