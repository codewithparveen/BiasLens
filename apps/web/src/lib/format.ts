export type SignalBand = "low" | "mid" | "high";

/** Inequality score: low is good (equal), high is bad (unequal). */
export function inequalityBand(score: number): SignalBand {
  if (score < 33) return "low";
  if (score < 66) return "mid";
  return "high";
}

/** Quality score: high is good, low is bad -- inverse of inequality bands. */
export function qualityBand(score: number): SignalBand {
  if (score >= 66) return "low"; // reuse "low" == green
  if (score >= 33) return "mid";
  return "high";
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatScore(value: number, digits = 1): string {
  return value.toFixed(digits);
}

const BAND_LABEL: Record<SignalBand, string> = {
  low: "Low",
  mid: "Moderate",
  high: "High",
};

export function bandLabel(band: SignalBand): string {
  return BAND_LABEL[band];
}
