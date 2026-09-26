import { describe, expect, it } from "vitest";
import { bandLabel, formatPercent, formatScore, inequalityBand, qualityBand } from "@/lib/format";

describe("inequalityBand", () => {
  it("bands low scores as low", () => {
    expect(inequalityBand(0)).toBe("low");
    expect(inequalityBand(32.9)).toBe("low");
  });
  it("bands mid-range scores as mid", () => {
    expect(inequalityBand(33)).toBe("mid");
    expect(inequalityBand(65.9)).toBe("mid");
  });
  it("bands high scores as high", () => {
    expect(inequalityBand(66)).toBe("high");
    expect(inequalityBand(100)).toBe("high");
  });
});

describe("qualityBand", () => {
  it("is the inverse of inequalityBand: high quality is good (low/green)", () => {
    expect(qualityBand(90)).toBe("low");
    expect(qualityBand(50)).toBe("mid");
    expect(qualityBand(10)).toBe("high");
  });
});

describe("formatPercent", () => {
  it("converts a 0-1 fraction to a whole-number percent by default", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(1)).toBe("100%");
    expect(formatPercent(0)).toBe("0%");
  });
  it("respects a custom digit count", () => {
    expect(formatPercent(0.4567, 1)).toBe("45.7%");
  });
});

describe("formatScore", () => {
  it("formats to one decimal place by default", () => {
    expect(formatScore(47.266)).toBe("47.3");
  });
  it("respects a custom digit count", () => {
    expect(formatScore(47.266, 2)).toBe("47.27");
  });
});

describe("bandLabel", () => {
  it("returns a human label for every band", () => {
    expect(bandLabel("low")).toBe("Low");
    expect(bandLabel("mid")).toBe("Moderate");
    expect(bandLabel("high")).toBe("High");
  });
});
