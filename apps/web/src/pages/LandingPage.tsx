import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Activity, GitFork, Languages, MapPinned, Mic, Search } from "lucide-react";
import { api, ApiRequestError } from "@/lib/api";
import type { FeaturedResponse, VariantMetrics } from "@/lib/types";
import { qualityBand, formatScore } from "@/lib/format";
import { DEMO_CITY_POSITIONS, IndiaMapPreview, type MapCity } from "@/components/IndiaMapPreview";
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, CopySnippet, Skeleton, ErrorState, buttonVariants } from "@/design-system/ui";
import { cn } from "@/lib/utils";
import { createSpeechRecognition } from "@/lib/speech";

const EXAMPLE_QUERIES = ["diabetes home remedy", "best crop loan", "covid vaccine side effects"];
const DEFAULT_CITIES = ["Chennai", "Delhi", "Bengaluru", "Mumbai", "Kolkata"];
const DEFAULT_LANGUAGES = ["ta", "hi", "en", "mr", "bn"];

const STEPS = [
  {
    title: "Pick a query",
    body: "Type anything people actually search for -- a health question, a loan, a government scheme -- in any language.",
  },
  {
    title: "BiasLens fetches it everywhere",
    body: "The same query runs against Google in five Indian cities, in each city's own language, through SerpApi.",
  },
  {
    title: "See who gets what",
    body: "Overlap, source quality, language match, and diversity are compared side by side, with one inequality score per query.",
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const [query, setQuery] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [listening, setListening] = React.useState(false);

  const startVoiceInput = () => {
    const recognition = createSpeechRecognition();
    if (!recognition) {
      setSubmitError("Voice input is unavailable in this browser. You can type the query instead.");
      return;
    }
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setQuery(transcript);
      setListening(false);
    };
    recognition.onerror = () => {
      setListening(false);
      setSubmitError("Could not hear that. Please try again or type the query.");
    };
    recognition.onend = () => setListening(false);
    setSubmitError(null);
    setListening(true);
    recognition.start();
  };

  const runAudit = React.useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) return;
      setSubmitting(true);
      setSubmitError(null);
      try {
        const { id } = await api.startAudit({
          queries: [trimmed],
          cities: DEFAULT_CITIES,
          languages: DEFAULT_LANGUAGES,
        });
        navigate(`/results/${id}?q=${encodeURIComponent(trimmed)}`);
      } catch (err) {
        setSubmitError(err instanceof ApiRequestError ? err.message : "Could not start that audit.");
        setSubmitting(false);
      }
    },
    [navigate],
  );

  return (
    <div className="min-h-screen bg-(--bg) text-(--fg)">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="inline-flex items-center gap-2 font-(family-name:--font-display) text-lg font-semibold">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-(--accent) text-xs text-(--accent-fg)">
            B
          </span>
          BiasLens
        </span>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 text-sm text-(--fg-muted) hover:text-(--fg)"
        >
          <GitFork className="h-4 w-4" /> Open source
        </a>
      </header>

      <main>
        <Hero
          query={query}
          onQueryChange={setQuery}
          onSubmit={() => runAudit(query)}
          onChipClick={(q) => {
            setQuery(q);
            runAudit(q);
          }}
          submitting={submitting}
          error={submitError}
          listening={listening}
          onVoiceInput={startVoiceInput}
        />
        <MapSection />
        <FeaturedSection />
        <HowItWorks />
        <InstallSection />
      </main>

      <footer className="mx-auto max-w-6xl px-6 py-10 text-center text-sm text-(--fg-muted)">
        Built for the SerpApi India Hackathon 2026. Findings are descriptive, not causal --
        see the methodology for what the inequality score does and doesn't claim.
      </footer>
    </div>
  );
}

interface HeroProps {
  query: string;
  onQueryChange: (v: string) => void;
  onSubmit: () => void;
  onChipClick: (q: string) => void;
  submitting: boolean;
  error: string | null;
  listening: boolean;
  onVoiceInput: () => void;
}

function Hero({
  query,
  onQueryChange,
  onSubmit,
  onChipClick,
  submitting,
  error,
  listening,
  onVoiceInput,
}: HeroProps) {
  return (
    <section className="mx-auto max-w-6xl px-6 pb-16 pt-12">
      <div className="mx-auto max-w-3xl text-center">
        <p className="mb-4 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-(--accent)">
          <Activity className="h-3.5 w-3.5" aria-hidden="true" /> Search equity, measured
        </p>
        <h1 className="font-(family-name:--font-display) text-4xl leading-[1.08] sm:text-6xl">
          Does India search the same question into two different answers?
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-(--fg-muted)">
          BiasLens audits one Google search across Indian cities and languages, then shows where
          people receive different sources, different language access, and different quality.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          className="mx-auto mt-8 flex max-w-2xl items-center gap-2 rounded-xl border border-(--border) bg-(--bg-elevated) p-2 pl-5 shadow-lg shadow-black/5"
        >
          <Search className="h-4 w-4 shrink-0 text-(--fg-muted)" aria-hidden="true" />
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Try a query, e.g. diabetes home remedy"
            aria-label="Search query to audit"
            className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-(--fg-muted)"
          />
          <button
            type="button"
            onClick={onVoiceInput}
            disabled={submitting || listening}
            aria-label={listening ? "Listening for search query" : "Search by voice"}
            title={listening ? "Listening…" : "Search by voice"}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-md text-(--fg-muted) transition-colors hover:bg-(--bg) hover:text-(--accent) disabled:opacity-50"
          >
            <Mic className={cn("h-4 w-4", listening && "animate-pulse text-(--signal-high-text)")} aria-hidden="true" />
          </button>
          <Button type="submit" size="md" disabled={submitting || !query.trim()}>
            {listening ? "Listening…" : submitting ? "Starting…" : "Run audit"}
          </Button>
        </form>

        {error && (
          <p role="alert" className="mt-3 text-sm text-(--signal-high-text)">
            {error}
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-(--fg-muted)">Try:</span>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onChipClick(q)}
              disabled={submitting}
              className="rounded-full border border-(--border) px-3 py-1 text-xs text-(--fg-muted) transition-colors hover:border-(--accent) hover:text-(--accent) disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-14 grid max-w-4xl border-y border-(--border) sm:grid-cols-3">
        <HeroSignal icon={MapPinned} value="5 cities" label="local search contexts" />
        <HeroSignal icon={Languages} value="5 languages" label="language access checks" />
        <HeroSignal icon={Activity} value="4 signals" label="one transparent score" />
      </div>
    </section>
  );
}

function HeroSignal({
  icon: Icon,
  value,
  label,
}: {
  icon: typeof Activity;
  value: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-3 border-(--border) px-5 py-4 sm:border-r last:border-r-0">
      <Icon className="h-4 w-4 shrink-0 text-(--accent)" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold">{value}</p>
        <p className="text-xs text-(--fg-muted)">{label}</p>
      </div>
    </div>
  );
}

function MapSection() {
  const [variants, setVariants] = React.useState<VariantMetrics[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { id } = await api.startAudit({
          queries: [EXAMPLE_QUERIES[0]],
          cities: DEFAULT_CITIES,
          languages: DEFAULT_LANGUAGES,
          demo: true,
        });
        const job = await api.pollAudit(id, { intervalMs: 300, timeoutMs: 10_000 });
        if (cancelled) return;
        if (job.status === "completed" && job.result) {
          setVariants(job.result.queries[0]?.variants ?? []);
        } else {
          setError(job.error ?? "Preview audit did not complete.");
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiRequestError ? err.message : "Could not load the preview.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const mapCities: MapCity[] = React.useMemo(() => {
    if (!variants) return [];
    return variants
      .filter((v) => DEMO_CITY_POSITIONS[v.variant.city])
      .map((v) => ({
        city: v.variant.city,
        ...DEMO_CITY_POSITIONS[v.variant.city],
        band: qualityBand(v.quality_score),
      }));
  }, [variants]);

  return (
    <section className="mx-auto max-w-4xl px-6 pb-16">
      <Card className="overflow-hidden">
        <CardContent className="grid gap-6 p-6 sm:grid-cols-[minmax(0,1fr)_260px] sm:items-center">
          <div className="mx-auto aspect-[500/560] w-full max-w-xs sm:mx-0">
            {error ? (
              <ErrorState message={error} />
            ) : mapCities.length ? (
              <IndiaMapPreview cities={mapCities} />
            ) : (
              <Skeleton className="h-full w-full" />
            )}
          </div>
          <div>
            <p className="font-(family-name:--font-display) text-xl">
              Source quality, city by city
            </p>
            <p className="mt-2 text-sm text-(--fg-muted)">
              This preview uses a saved demo audit for "{EXAMPLE_QUERIES[0]}" and colors each
              city by how trustworthy its top results were -- green for government/health-authority-heavy
              results, red for forum- and commercial-heavy results.
            </p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function FeaturedSection() {
  const [data, setData] = React.useState<FeaturedResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    api
      .featured()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiRequestError ? err.message : "Could not load findings.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mx-auto max-w-6xl px-6 pb-16">
      <h2 className="font-(family-name:--font-display) text-2xl">Featured findings</h2>
      <p className="mt-1 text-sm text-(--fg-muted)">
        {data?.is_demo_data
          ? "Demo data -- synthetic input run through the real scoring engine, pending a live audit."
          : "Headline numbers from the latest audits."}
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {error && <ErrorState message={error} />}
        {!data && !error && Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
        {data?.queries.map((q) => (
          <Card key={q.slug}>
            <CardHeader>
              <CardTitle className="text-base leading-snug">{q.query}</CardTitle>
              <CardDescription>Information Inequality Score</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="font-(family-name:--font-display) text-4xl">{formatScore(q.inequality_score)}</p>
              <p className="text-xs text-(--fg-muted)">out of 100</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section className="mx-auto max-w-4xl px-6 pb-16">
      <h2 className="font-(family-name:--font-display) text-2xl">How it works</h2>
      <div className="mt-6 grid gap-6 sm:grid-cols-3">
        {STEPS.map((step) => (
          <div key={step.title} className="border-t-2 border-(--accent) pt-3">
            <p className="font-medium">{step.title}</p>
            <p className="mt-1 text-sm text-(--fg-muted)">{step.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function InstallSection() {
  return (
    <section className="mx-auto max-w-2xl px-6 pb-20 text-center">
      <h2 className="font-(family-name:--font-display) text-2xl">Open source, audit it yourself</h2>
      <p className="mt-2 text-sm text-(--fg-muted)">
        The library behind this dashboard is pip-installable and MIT licensed.
      </p>
      <div className="mt-6">
        <CopySnippet code="pip install biaslens" />
      </div>
      <a
        href="https://github.com"
        target="_blank"
        rel="noreferrer"
        className={cn(buttonVariants({ variant: "secondary" }), "mt-4 inline-flex items-center gap-2")}
      >
        <GitFork className="h-4 w-4" /> View on GitHub
      </a>
    </section>
  );
}
