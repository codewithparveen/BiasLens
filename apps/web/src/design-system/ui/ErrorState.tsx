import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message: string;
  hint?: string | null;
  onRetry?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, hint, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-(--radius-card) border border-(--border) bg-(--bg-elevated) p-8 text-center">
      <AlertTriangle className="h-6 w-6 text-(--signal-high-text)" aria-hidden="true" />
      <div>
        <p className="font-medium text-(--fg)">{title}</p>
        <p className="mt-1 text-sm text-(--fg-muted)">{message}</p>
        {hint && <p className="mt-1 text-xs text-(--fg-muted)">{hint}</p>}
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallbackMessage?: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorState
          title="This section couldn't load"
          message={this.props.fallbackMessage ?? this.state.error.message}
          onRetry={() => this.setState({ error: null })}
        />
      );
    }
    return this.props.children;
  }
}
