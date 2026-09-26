import * as React from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { Download, ImageDown, LinkIcon, ArrowLeft, Volume2, VolumeX } from "lucide-react";
import { toPng } from "html-to-image";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiRequestError } from "@/lib/api";
import type { AuditJob, QueryAuditResult, VariantMetrics } from "@/lib/types";
import { bandLabel, formatPercent, formatScore, inequalityBand, qualityBand, type SignalBand } from "@/lib/format";
import { DEMO_CITY_POSITIONS, IndiaMapPreview, type MapCity } from "@/components/IndiaMapPreview";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Skeleton,
  ErrorState,
  Tooltip,
} from "@/design-system/ui";

const TIER_COLOR: Record<string, string> = {
  government_official: "#17497f",
  health_medical_authority: "#3f7d5c",
  academic: "#2b6e63",
  consumer_health_media: "#6a9b7f",
  established_news: "#3f7cb8",
  commercial: "#c08a1e",
  forum_ugc: "#c46a2e",
  low_quality_content_farm: "#b33d2e",
  unclassified: "#9c8c7f",
};

const SCORE_METRICS: { key: keyof QueryAuditResult["score_breakdown"]; label: string; help: string }[] = [
  { key: "overlap", label: "Result Overlap", help: "How different the actual top-10 result sets are across cities/languages (rank-biased overlap)." },
  { key: "quality", label: "Source Quality", help: "How unevenly trustworthy the sources are -- spread of weighted domain-tier scores across variants." },
  { key: "language", label: "Language Match", help: "How unevenly results actually match the query's language across variants." },
  { key: "diversity", label: "Source Diversity", help: "How unevenly diverse the domain mix is (Shannon entropy) across variants." },
];

function buildExplanation(result: QueryAuditResult): string {
  const breakdown = result.score_breakdown;
  const strongest = Object.entries(breakdown).sort(([, first], [, second]) => second - first)[0]?.[0];
  const highest = result.variants.reduce((best, current) =>
    current.quality_score > best.quality_score ? current : best,
  );
  const lowest = result.variants.reduce((worst, current) =>
    current.quality_score < worst.quality_score ? current : worst,
  );

  const driver =
    strongest === "overlap"
      ? "the city-language variants returned different top results"
      : strongest === "quality"
        ? "source quality varied most between the variants"
        : strongest === "language"
          ? "language matching varied most between the variants"
          : "source diversity varied most between the variants";

  return `The main signal is ${driver}. ${highest.variant.city} had the strongest source-quality mix (${formatScore(highest.quality_score)}), while ${lowest.variant.city} was lowest (${formatScore(lowest.quality_score)}). This describes the observed search results; it does not claim why the difference happened.`;
}

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const queryHint = searchParams.get("q");

  const [job, setJob] = React.useState<AuditJob | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  React.useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setJob(null);
    setError(null);
    api
      .pollAudit(jobId, { intervalMs: 800, timeoutMs: 90_000 })
      .then((result) => {
        if (!cancelled) setJob(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiRequestError ? err.message : "Could not load this audit.");
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, attempt]);

  return (
    <div className="min-h-screen bg-(--bg) text-(--fg)">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-(--fg-muted) hover:text-(--fg)">
          <ArrowLeft className="h-4 w-4" /> BiasLens
        </Link>
        {job?.result?.is_demo_data && <Badge tone="accent">Demo data</Badge>}
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        {error && <ErrorState message={error} onRetry={() => setAttempt((n) => n + 1)} />}

        {!error && !job && <LoadingState queryHint={queryHint} />}

        {!error && job?.status === "failed" && (
          <ErrorState
            title="Audit failed"
            message={job.error ?? "The audit could not complete."}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}

        {job?.status === "completed" && job.result && job.result.queries[0] && (
          <ResultsView report={job.result} result={job.result.queries[0]} jobId={jobId!} />
        )}
      </main>
    </div>
  );
}

function LoadingState({ queryHint }: { queryHint: string | null }) {
  return (
    <div className="py-10">
      <p className="text-sm text-(--fg-muted)">
        {queryHint ? `Auditing "${queryHint}" across cities and languages…` : "Running audit…"}
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    </div>
  );
}

function ResultsView({
  report,
  result,
  jobId,
}: {
  report: NonNullable<AuditJob["result"]>;
  result: QueryAuditResult;
  jobId: string;
}) {
  const band = inequalityBand(result.inequality_score);
  const captureRef = React.useRef<HTMLDivElement>(null);
  const [exportingPng, setExportingPng] = React.useState(false);
  const [speaking, setSpeaking] = React.useState(false);

  const mapCities: MapCity[] = result.variants
    .filter((v) => DEMO_CITY_POSITIONS[v.variant.city])
    .map((v) => ({
      city: v.variant.city,
      ...DEMO_CITY_POSITIONS[v.variant.city],
      band: qualityBand(v.quality_score),
    }));

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `biaslens-${result.query.replace(/\s+/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // clipboard can be unavailable -- silently ignore, same as CopySnippet
    }
  };

  const handleExportPng = async () => {
    if (!captureRef.current || exportingPng) return;
    setExportingPng(true);
    try {
      const dataUrl = await toPng(captureRef.current, {
        backgroundColor: getComputedStyle(document.body).getPropertyValue("--bg-page") || "#ffffff",
        pixelRatio: 2,
        filter: (node) => !(node instanceof HTMLElement && node.hasAttribute("data-export-exclude")),
      });
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `biaslens-${result.query.replace(/\s+/g, "-")}.png`;
      a.click();
    } catch {
      // best-effort export -- e.g. a chart hasn't finished rendering yet
    } finally {
      setExportingPng(false);
    }
  };

  const handleSpeak = () => {
    if (!("speechSynthesis" in window)) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(buildExplanation(result));
    utterance.lang = "en-IN";
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div ref={captureRef} className="py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-(--fg-muted)">Audit results for</p>
          <h1 className="font-(family-name:--font-display) text-3xl">{result.query}</h1>
        </div>
        <div className="flex gap-2" data-export-exclude="true">
          <Button variant="secondary" size="sm" onClick={handleCopyLink}>
            <LinkIcon className="mr-1.5 h-3.5 w-3.5" /> Copy link
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExportJson}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> Export JSON
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExportPng} disabled={exportingPng}>
            <ImageDown className="mr-1.5 h-3.5 w-3.5" /> {exportingPng ? "Exporting..." : "Export PNG"}
          </Button>
        </div>
      </div>

      {report.warnings.length > 0 && (
        <p className="mt-4 rounded-md border border-(--border) bg-(--bg-elevated) p-3 text-xs text-(--fg-muted)">
          {report.warnings[0]}
        </p>
      )}

      <section className="mt-6 rounded-(--radius-card) border border-(--accent)/30 bg-(--accent)/8 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-(--accent)">Explain layer</p>
            <h2 className="mt-1 font-(family-name:--font-display) text-xl">What this score is saying</h2>
          </div>
          <Badge tone="accent">Computed from audit metrics</Badge>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-(--fg-muted)">{buildExplanation(result)}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button variant="secondary" size="sm" onClick={handleSpeak}>
            {speaking ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            {speaking ? "Stop reading" : "Read aloud"}
          </Button>
          <p className="text-xs text-(--fg-muted)">
            Computed from the measured breakdown; it does not change the score or add outside facts.
          </p>
        </div>
      </section>

      <section className="mt-8 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardDescription>Information Inequality Score</CardDescription>
            <div className="flex items-baseline gap-2">
              <CardTitle className="text-5xl">{formatScore(result.inequality_score)}</CardTitle>
              <Badge tone={band}>{bandLabel(band)}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {SCORE_METRICS.map((m) => (
              <Tooltip key={m.key} content={m.help}>
                <div className="flex items-center justify-between text-xs">
                  <span className="cursor-help text-(--fg-muted) underline decoration-dotted">{m.label}</span>
                  <span>{formatPercent(result.score_breakdown[m.key])}</span>
                </div>
              </Tooltip>
            ))}
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardContent className="p-4">
            <div className="mx-auto aspect-[500/560] max-w-[240px]">
              <IndiaMapPreview cities={mapCities} />
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="mt-10">
        <h2 className="font-(family-name:--font-display) text-xl">Results by city and language</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {result.variants.map((v) => (
            <VariantCard key={v.label} variant={v} />
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-(family-name:--font-display) text-xl">Source quality mix</h2>
        <Card className="mt-4">
          <CardContent className="p-4">
            <QualityMixChart variants={result.variants} />
          </CardContent>
        </Card>
      </section>

      <section className="mt-10">
        <h2 className="font-(family-name:--font-display) text-xl">Overlap matrix</h2>
        <p className="mt-1 text-sm text-(--fg-muted)">Rank-biased overlap between each pair of variants (1.0 = identical top results).</p>
        <Card className="mt-4 overflow-x-auto">
          <CardContent className="p-4">
            <OverlapMatrix result={result} />
          </CardContent>
        </Card>
      </section>

      <p className="mt-10 text-xs text-(--fg-muted)">
        Job ID: <code className="font-(family-name:--font-mono)">{jobId}</code> · Sample size: 1 query x{" "}
        {result.variants.length} city/language variants. Descriptive only -- see methodology for limitations.
      </p>
    </div>
  );
}

function VariantCard({ variant }: { variant: VariantMetrics }) {
  const band = qualityBand(variant.quality_score);
  const tiers = Object.entries(variant.quality_mix).sort((a, b) => b[1].count - a[1].count);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{variant.variant.city}</CardTitle>
          <span className="text-xs uppercase text-(--fg-muted)">{variant.variant.language}</span>
        </div>
        <CardDescription>
          {variant.is_empty ? "No results returned" : `${variant.result_count} results`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {tiers.map(([tier, entry]) => (
            <Badge key={tier} tone={qualityBand(entry.weight * 100)}>
              {entry.label} · {entry.count}
            </Badge>
          ))}
        </div>
        <dl className="grid grid-cols-2 gap-2 text-xs">
          <Metric label="Quality" value={formatScore(variant.quality_score)} tone={band} />
          <Metric label="Language match" value={formatPercent(variant.language_match_rate)} />
          <Metric label="Diversity" value={formatScore(variant.normalized_entropy, 2)} />
          <Metric label="Ads" value={String(variant.ad_count)} />
        </dl>
      </CardContent>
    </Card>
  );
}

const SIGNAL_TEXT_CLASS: Record<SignalBand, string> = {
  low: "text-(--signal-low-text)",
  mid: "text-(--signal-mid-text)",
  high: "text-(--signal-high-text)",
};

function Metric({ label, value, tone }: { label: string; value: string; tone?: SignalBand }) {
  return (
    <div>
      <dt className="text-(--fg-muted)">{label}</dt>
      <dd className={tone ? `font-medium ${SIGNAL_TEXT_CLASS[tone]}` : "font-medium"}>{value}</dd>
    </div>
  );
}

function QualityMixChart({ variants }: { variants: VariantMetrics[] }) {
  const tierKeys = React.useMemo(() => {
    const keys = new Set<string>();
    variants.forEach((v) => Object.keys(v.quality_mix).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [variants]);

  const data = variants.map((v) => {
    const row: Record<string, string | number> = { name: v.label };
    tierKeys.forEach((tier) => {
      row[tier] = (v.quality_mix[tier]?.share ?? 0) * 100;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis type="number" unit="%" tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
        <RechartsTooltip
          formatter={(value) => (typeof value === "number" ? `${value.toFixed(0)}%` : `${value}%`)}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {tierKeys.map((tier) => (
          <Bar key={tier} dataKey={tier} stackId="mix" fill={TIER_COLOR[tier] ?? "#9c8c7f"} name={tier.replace(/_/g, " ")} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function OverlapMatrix({ result }: { result: QueryAuditResult }) {
  const labels = result.variants.map((v) => v.label);
  const lookup = new Map<string, number>();
  result.pairwise.forEach((p) => {
    lookup.set(`${p.variant_a}|${p.variant_b}`, p.rbo);
    lookup.set(`${p.variant_b}|${p.variant_a}`, p.rbo);
  });

  return (
    <table className="w-full min-w-[480px] border-collapse text-xs">
      <thead>
        <tr>
          <th className="p-2 text-left text-(--fg-muted)"></th>
          {labels.map((l) => (
            <th key={l} className="p-2 text-left font-medium text-(--fg-muted)">
              {l}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {labels.map((rowLabel) => (
          <tr key={rowLabel} className="border-t border-(--border)">
            <th className="p-2 text-left font-medium text-(--fg-muted)">{rowLabel}</th>
            {labels.map((colLabel) => {
              if (rowLabel === colLabel) {
                return (
                  <td key={colLabel} className="p-2 text-(--fg-muted)">
                    —
                  </td>
                );
              }
              const value = lookup.get(`${rowLabel}|${colLabel}`);
              return (
                <td key={colLabel} className="p-2">
                  {value !== undefined ? value.toFixed(2) : "—"}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
