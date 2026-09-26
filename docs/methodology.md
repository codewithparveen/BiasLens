# BiasLens Methodology

This document is the source of truth for every metric BiasLens reports.
Every number in the dashboard traces back to a formula here, computed in
plain Python (`biaslens/metrics/`) — never guessed by an LLM. The optional
LLM layer (`explain.py`, Step 4+) only writes prose *about* numbers that
were already computed by this pipeline; it cannot alter them.

## 1. Result Overlap

For two (city, language) variants of the same query, we compare their
top-N organic result domains two ways:

- **Jaccard similarity**: `|A ∩ B| / |A ∪ B|` over the *set* of domains.
  Ignores rank order — a quick "how much of the same web is showing up."
- **Rank-biased overlap (RBO)**, Webber, Moffat & Zobel (2010): unlike
  Jaccard, RBO weights agreement at higher ranks more heavily, since a
  domain at position 1 matters more than one at position 10. We use the
  paper's extrapolated formula with persistence `p = 0.9` (top ~10 ranks
  carry ~86% of the weight), computed over `k = min(len(A), len(B))`.

  **Known simplification**: when the two lists are unequal length, the
  original paper defines a more involved extrapolation that accounts for
  the longer list's "unseen" tail. We instead truncate both lists to the
  shorter one's length and compute the equal-length formula on that
  truncation. This is a documented approximation, not the full paper
  formula, and is only relevant when a fetch returned fewer than
  `num_results` for one variant (e.g. a partial result set).

Both scores are in `[0, 1]`, where 1 = identical, 0 = no shared domains
within the compared depth.

## 2. Source Quality Mix

Every result domain is classified into exactly one tier via a suffix
lookup against `domain_tiers.yaml` — a plain, editable, version-controlled
file (government/official, academic, health/medical authority, consumer
health media, established news, commercial, forum/UGC, low-quality/
content farm, or unclassified). **No LLM is involved in classification** —
this is deliberate, so results are reproducible and any miscategorization
is a one-line YAML fix, not a black box.

Each tier carries a `weight` in `[0, 1]` (government/official = 1.0 down to
low-quality/content-farm = 0.1). A variant's **weighted quality score** is
the mean tier weight across its results, scaled to `[0, 100]`.

**Known limitation**: the tier list is necessarily incomplete and reflects
our own editorial judgment about source reliability for Indian contexts.
The `low_quality_content_farm` tier intentionally ships empty — we only
add a domain there from evidence seen in an actual audit run (thin,
duplicated, or AI-spun content), never by reputation alone.

## 3. Language Match Rate

Fraction of a variant's organic-result snippets that are actually written
in the language the query was issued in (the `hl` param). We detect this
with a **Unicode-script heuristic**, not a statistical language-ID model:
for each Indic language we check what fraction of alphabetic characters
fall in that script's Unicode block (e.g. Tamil: U+0B80–U+0BFF); for
English, what fraction are ASCII Latin letters. A text "matches" if that
ratio clears a 0.5 threshold.

**Known limitation**: script ≠ language. Hindi and Marathi share the
Devanagari block and are indistinguishable by this heuristic alone;
transliterated text (Tamil written in Latin script) will not match Tamil;
code-mixed text is scored by whichever script is more frequent. We accept
this trade-off for a hackathon-scale, dependency-light implementation and
call it out wherever the metric is displayed.

## 4. Source Diversity

Shannon entropy (bits) over the domain frequency distribution of a
variant's results: `-Σ p(d) · log2(p(d))` for each distinct domain `d`.
We also report **normalized entropy** (`entropy / log2(distinct domains)`,
range `[0, 1]`) so diversity is comparable across variants with different
result counts.

## 5. Ad Load and AI-Overview Presence

Reported directly from the SerpApi response: number of `ads` entries, and
a boolean for whether an `ai_overview` block was present. No derived
formula — these are read as-is per variant.

## 6. Reliability (Run-to-Run Variance)

Every variant is fetched `N` times (default 2, configurable). For any
numeric metric, we report `mean`, `stdev` (population stdev across the
N runs), and `coefficient_of_variation` (`stdev / mean`, `None` if
`mean == 0`). This exists to separate **real cross-variant bias** (a
persistent difference between Chennai and Delhi, say) from **Google's own
result churn** (the same variant returning slightly different results on
two calls seconds apart). A high inequality score alongside high
within-variant variance should be read with more caution than the same
score with low variance.

## 7. Information Inequality Score (0–100)

The single headline number, combining four already-computed signals into
one weighted sum. Each component is normalized to `[0, 1]` first:

| Component | What it measures | Formula | Weight |
|---|---|---|---|
| Overlap | How different the actual result sets are across variants | `1 − mean(pairwise RBO)` | 0.40 |
| Quality | How unevenly trustworthy the sources are across variants | `(max − min)` of per-variant weighted quality scores, ÷ 100 | 0.20 |
| Language | How unevenly results match the query's language across variants | `(max − min)` of per-variant language match rates | 0.25 |
| Diversity | How unevenly diverse the source mix is across variants | `(max − min)` of per-variant normalized entropy | 0.15 |

```
score = 100 × (0.40·overlap + 0.20·quality + 0.25·language + 0.15·diversity)
```

**Why these weights**: overlap is weighted highest because it is the most
direct evidence that two people literally see a different web. Language
is weighted above quality because for a multilingual country, being
served content in the wrong language is functionally being denied
information — an access problem, not just a quality one. Diversity is
weighted lowest because it is the most indirect signal (a narrow-but-
authoritative source mix, e.g. all `.gov.in`, is not necessarily bad).

These weights are a documented editorial judgment, not a derived
constant — `weights=` is a keyword argument on
`information_inequality_score()` precisely so this can be interrogated
and changed. We report the full component breakdown alongside the total
specifically so no one has to trust a single number blindly.

**What the score is not**: a causal claim about *why* results differ (could
be genuine content availability, Google's ranking signals, or something
else), and not a measure of absolute quality — a score of 0 does not mean
"good information everywhere," only "equally served information."

## 8. Sample Size and Limitations (applies to every audit)

- Every reported finding should state its `N` (queries × cities ×
  languages × runs) — see `docs/methodology.md` companion in the
  README's findings section once real audit data exists.
- SerpApi's free-plan volume (~250 searches/month) bounds how many
  queries, cities, and languages a given audit can cover; see the credit
  budget in the project plan.
- Results reflect a snapshot in time; Google's SERPs change continuously.
- No claim in this project should be read as causal ("City X is
  discriminated against") — only descriptive ("City X's top-10 results for
  query Y overlapped Z% with City W's, on this date").
