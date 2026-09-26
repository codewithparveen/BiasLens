import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * A deliberately simplified India outline + city markers rather than a full
 * choropleth over real state-boundary GeoJSON. Positions below are hand
 *-projected from real city lat/long onto a fixed 0-500 x 0-560 viewBox
 * (equirectangular-ish, tuned by eye against India's actual outline) --
 * good enough for "where is this city and how unequal is it" at a glance,
 * not for precise geographic analysis. Callers pass a precomputed signal
 * band per city (see lib/format.ts qualityBand/inequalityBand) rather than
 * a raw score, so this component stays agnostic to which metric is being
 * mapped. Swap in real d3-geo + bundled state-boundary GeoJSON here if the project needs cartographic accuracy
 * later (see docs/methodology.md limitations section for the same
 * proportionality trade-off applied to the metrics themselves).
 */

export interface MapCity {
  city: string;
  x: number;
  y: number;
  band: "low" | "mid" | "high";
}

const SIGNAL_HEX: Record<"low" | "mid" | "high", string> = {
  low: "#3f7d5c",
  mid: "#c08a1e",
  high: "#b33d2e",
};

// Hand-projected approximate positions within the 0-500 x 0-560 viewBox.
export const DEMO_CITY_POSITIONS: Record<string, { x: number; y: number }> = {
  Chennai: { x: 300, y: 430 },
  Delhi: { x: 235, y: 130 },
  Bengaluru: { x: 265, y: 400 },
  Mumbai: { x: 175, y: 280 },
  Kolkata: { x: 400, y: 240 },
  Hyderabad: { x: 280, y: 330 },
  Ahmedabad: { x: 150, y: 210 },
};

interface IndiaMapPreviewProps {
  cities: MapCity[];
  className?: string;
  onSelectCity?: (city: string) => void;
  selectedCity?: string | null;
}

export function IndiaMapPreview({ cities, className, onSelectCity, selectedCity }: IndiaMapPreviewProps) {
  return (
    <div className={cn("relative", className)}>
      <svg viewBox="0 0 500 560" className="h-full w-full" role="img" aria-label="Map of audited Indian cities">
        {/* Simplified India silhouette -- a rough, stylized outline, not a
            precise state-boundary trace. */}
        <path
          d="M230 20 L280 35 L300 70 L340 90 L360 130 L400 150 L430 200 L420 240
             L440 270 L420 310 L430 350 L400 380 L390 420 L350 450 L340 490
             L310 520 L290 500 L270 470 L250 480 L230 450 L210 460 L190 420
             L160 400 L150 360 L120 340 L110 290 L130 260 L120 220 L150 190
             L140 150 L170 110 L160 70 L190 50 Z"
          fill="var(--color-ink-100)"
          stroke="var(--border)"
          strokeWidth="2"
          className="dark:fill-(--color-ink-800)"
        />
        {cities.map((c) => {
          const isSelected = selectedCity === c.city;
          return (
            <g
              key={c.city}
              transform={`translate(${c.x}, ${c.y})`}
              className={onSelectCity ? "cursor-pointer" : undefined}
              onClick={() => onSelectCity?.(c.city)}
            >
              <motion.circle
                r={isSelected ? 14 : 10}
                fill={SIGNAL_HEX[c.band]}
                fillOpacity={0.85}
                stroke="var(--bg-elevated)"
                strokeWidth={2}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              />
              <motion.circle
                r={10}
                fill="none"
                stroke={SIGNAL_HEX[c.band]}
                strokeWidth={1.5}
                initial={{ opacity: 0.6, scale: 1 }}
                animate={{ opacity: 0, scale: 2.2 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
              />
              <text
                y={-18}
                textAnchor="middle"
                className="fill-(--fg) font-(family-name:--font-sans) text-[11px] font-medium"
              >
                {c.city}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
