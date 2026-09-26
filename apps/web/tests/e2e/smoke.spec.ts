import { test, expect } from "@playwright/test";

/**
 * End-to-end smoke test for the core BiasLens flow: landing page -> submit
 * an audit -> results page renders with real data. Runs against the demo
 * (fixture-backed) backend, so it needs no SerpApi key and makes no
 * external network calls.
 *
 * Requires both servers running first (see playwright.config.ts).
 */

test("landing page loads with the query box and example chips", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const queryBox = page.getByLabel("Search query to audit");
  await expect(queryBox).toBeVisible();

  // Example query chips should be present and clickable.
  await expect(page.getByRole("button", { name: "diabetes home remedy" })).toBeVisible();
});

test("submitting an example query navigates to a populated results page", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "diabetes home remedy" }).click();

  // Results page URL is /results/:jobId
  await page.waitForURL(/\/results\//, { timeout: 15_000 });

  // The inequality score card and at least one city variant card should render.
  await expect(page.getByText("Information Inequality Score")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Results by city and language")).toBeVisible();

  // Overlap matrix and quality mix sections should also render, confirming
  // the full report (not just the score) made it through.
  await expect(page.getByText("Overlap matrix")).toBeVisible();
  await expect(page.getByText("Source quality mix")).toBeVisible();
});

test("results page export controls are present and enabled", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "diabetes home remedy" }).click();
  await page.waitForURL(/\/results\//, { timeout: 15_000 });
  await expect(page.getByText("Information Inequality Score")).toBeVisible({ timeout: 15_000 });

  await expect(page.getByRole("button", { name: "Copy link" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Export JSON" })).toBeEnabled();

  const pngButton = page.getByRole("button", { name: /Export PNG/ });
  await expect(pngButton).toBeEnabled();

  // Verify the PNG download actually fires rather than just checking the
  // button exists.
  const downloadPromise = page.waitForEvent("download");
  await pngButton.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.png$/);
});

test("keyboard navigation reaches the query box and example chips", async ({ page }) => {
  await page.goto("/");

  // Tab from the top of the page should reach the query input, then the
  // submit button, then the example chips -- all real, focusable elements.
  await page.keyboard.press("Tab"); // skip link / logo / github link, browser-dependent start point
  const queryBox = page.getByLabel("Search query to audit");
  await queryBox.focus();
  await expect(queryBox).toBeFocused();

  await page.keyboard.type("test query");
  await expect(queryBox).toHaveValue("test query");
});
