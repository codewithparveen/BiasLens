/**
 * Hand-mirrored types for the BiasLens backend's JSON responses.
 *
 * Kept in sync manually with packages/biaslens/src/biaslens/report.py and
 * models.py rather than code-generated, since the API surface is still
 * small. If the backend schema grows a lot, swap this for an OpenAPI
 * codegen step (`openapi-typescript`) pointed at FastAPI's /openapi.json.
 */

export interface SearchVariant {
  query: string;
  city: string;
  language: string;
  google_domain: string;
  country: string;
  num_results: number;
}

export interface QualityMixEntry {
  count: number;
  share: number;
  label: string;
  weight: number;
}

export interface ReliabilityStat {
  n: number;
  mean: number;
  stdev: number;
  coefficient_of_variation: number | null;
}

export interface VariantMetrics {
  variant: SearchVariant;
  label: string;
  result_count: number;
  domains: string[];
  quality_mix: Record<string, QualityMixEntry>;
  quality_score: number;
  normalized_entropy: number;
  language_match_rate: number;
  ad_count: number;
  ai_overview_present: boolean;
  is_empty: boolean;
  reliability: Record<string, ReliabilityStat>;
  warnings: string[];
}

export interface PairwiseComparisonResult {
  variant_a: string;
  variant_b: string;
  jaccard: number;
  rbo: number;
}

export interface ScoreBreakdown {
  overlap: number;
  quality: number;
  language: number;
  diversity: number;
}

export interface QueryAuditResult {
  query: string;
  variants: VariantMetrics[];
  pairwise: PairwiseComparisonResult[];
  inequality_score: number;
  score_breakdown: ScoreBreakdown;
  score_weights: ScoreBreakdown;
}

export interface AuditPlan {
  queries: string[];
  cities: string[];
  languages: string[];
  runs_per_variant: number;
  google_domain: string;
  country: string;
  num_results: number;
}

export interface AuditReport {
  plan: AuditPlan;
  queries: QueryAuditResult[];
  generated_at: string;
  credits_used: number;
  cache_hits: number;
  is_demo_data: boolean;
  warnings: string[];
}

export interface CreditBudget {
  search_calls: number;
  trends_calls: number;
  total_credits: number;
  cache_hits_expected: number;
  max_credits: number | null;
  within_budget: boolean;
}

export interface EstimateResult {
  plan: AuditPlan;
  budget: CreditBudget;
  variants_preview: SearchVariant[];
}

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface AuditJobProgress {
  completed_queries?: number;
  total_queries?: number;
  current_query?: string;
  completed?: boolean;
}

export interface AuditJob {
  id: string;
  status: JobStatus;
  progress: AuditJobProgress;
  result: AuditReport | null;
  error: string | null;
}

export interface FeaturedQuery {
  slug: string;
  query: string;
  inequality_score: number;
}

export interface FeaturedResponse {
  is_demo_data: boolean;
  queries: FeaturedQuery[];
}

export interface Location {
  city: string;
  default_language: string;
  supported_languages: string[];
}

export interface ApiError {
  code: string;
  message: string;
  hint: string | null;
}
