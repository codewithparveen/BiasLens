"""Domain quality classification, driven entirely by domain_tiers.yaml.

Classification is a plain suffix lookup against editable YAML data -- never
an LLM guess -- so results are reproducible and the taxonomy is a one-file
PR away from being corrected.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import BiasLensError


@dataclass(frozen=True)
class TierMatch:
    tier: str
    label: str
    weight: float


class DomainTierClassifier:
    """Loads domain_tiers.yaml once and classifies domains against it."""

    def __init__(self, yaml_path: str | Path | None = None) -> None:
        if yaml_path is None:
            raw = resources.files("biaslens").joinpath("domain_tiers.yaml").read_text(encoding="utf-8")
        else:
            path = Path(yaml_path)
            if not path.exists():
                raise BiasLensError(f"Domain tier file not found: {path}")
            raw = path.read_text(encoding="utf-8")

        data: dict[str, Any] = yaml.safe_load(raw) or {}
        tiers_raw: dict[str, Any] = data.get("tiers", {})
        unclassified_raw: dict[str, Any] = data.get("unclassified", {"weight": 0.5, "label": "Unclassified"})

        # Flatten to a list of (suffix_or_exact_pattern, TierMatch), longest
        # pattern first so the most specific suffix wins (e.g. "aiims.edu"
        # before ".edu").
        self._patterns: list[tuple[str, TierMatch]] = []
        for tier_key, tier_data in tiers_raw.items():
            match = TierMatch(
                tier=tier_key,
                label=tier_data.get("label", tier_key),
                weight=float(tier_data.get("weight", 0.5)),
            )
            for pattern in tier_data.get("domains", []):
                self._patterns.append((pattern, match))
        self._patterns.sort(key=lambda item: len(item[0]), reverse=True)

        self._unclassified = TierMatch(
            tier="unclassified",
            label=unclassified_raw.get("label", "Unclassified"),
            weight=float(unclassified_raw.get("weight", 0.5)),
        )

    def classify(self, domain: str | None) -> TierMatch:
        if not domain:
            return self._unclassified
        domain = domain.lower().removeprefix("www.")
        for pattern, match in self._patterns:
            if pattern.startswith("."):
                if domain.endswith(pattern) or domain == pattern.lstrip("."):
                    return match
            elif domain == pattern:
                return match
        return self._unclassified

    def quality_mix(self, domains: list[str]) -> dict[str, dict[str, float | int | str]]:
        """Tier -> {count, share, label, weight} for a list of domains."""
        total = len(domains)
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        weights: dict[str, float] = {}
        for d in domains:
            match = self.classify(d)
            counts[match.tier] = counts.get(match.tier, 0) + 1
            labels[match.tier] = match.label
            weights[match.tier] = match.weight
        return {
            tier: {
                "count": count,
                "share": (count / total) if total else 0.0,
                "label": labels[tier],
                "weight": weights[tier],
            }
            for tier, count in counts.items()
        }

    def weighted_quality_score(self, domains: list[str]) -> float:
        """Mean tier weight across the given domains, scaled to 0-100. 0 if empty."""
        if not domains:
            return 0.0
        total_weight = sum(self.classify(d).weight for d in domains)
        return (total_weight / len(domains)) * 100
