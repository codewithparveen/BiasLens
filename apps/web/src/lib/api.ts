import type {
  ApiError,
  AuditJob,
  EstimateResult,
  FeaturedResponse,
  Location,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiRequestError extends Error {
  readonly code: string;
  readonly hint: string | null;
  readonly status: number;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = error.code;
    this.hint = error.hint;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiRequestError(0, {
      code: "network_error",
      message: "Could not reach the BiasLens backend. Is it running?",
      hint: "Start the backend with `uvicorn app.main:app --reload` and retry.",
    });
  }

  if (!response.ok) {
    let error: ApiError;
    try {
      error = (await response.json()) as ApiError;
    } catch {
      error = { code: "unknown_error", message: response.statusText, hint: null };
    }
    throw new ApiRequestError(response.status, error);
  }

  return (await response.json()) as T;
}

export interface EstimatePayload {
  queries: string[];
  cities: string[];
  languages: string[];
  runs_per_variant?: number;
  max_credits?: number | null;
}

export interface StartAuditPayload extends EstimatePayload {
  demo?: boolean;
}

export const api = {
  health: () => request<{ status: string; live_mode_available: boolean }>("/health"),

  locations: () => request<Location[]>("/locations"),

  featured: () => request<FeaturedResponse>("/featured"),

  estimate: (payload: EstimatePayload) =>
    request<EstimateResult>("/estimate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  startAudit: (payload: StartAuditPayload) =>
    request<{ id: string; status: string }>("/audits", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getAudit: (id: string) => request<AuditJob>(`/audits/${id}`),

  /** Poll an audit job until it's completed or failed. */
  async pollAudit(
    id: string,
    { intervalMs = 800, timeoutMs = 90_000 }: { intervalMs?: number; timeoutMs?: number } = {},
  ): Promise<AuditJob> {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const job = await api.getAudit(id);
      if (job.status === "completed" || job.status === "failed") {
        return job;
      }
      if (Date.now() > deadline) {
        throw new ApiRequestError(408, {
          code: "poll_timeout",
          message: "Audit is taking longer than expected.",
          hint: "The job may still complete -- check back shortly.",
        });
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  },
};
