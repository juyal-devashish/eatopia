import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { runToFinish, startOnboarding } from "./flow";

// The end-to-end API runs with LLM_TRANSPORT=offline, so the summary comes from a labelled stand-in.

test("both orders for one member appear side by side, counts first", async ({ page }) => {
  await startOnboarding(page, "A", "Today's order");
  await runToFinish(page);
  await page.getByRole("button", { name: "Try another member or order" }).click();
  await startOnboarding(page, "A", "Health first");
  await runToFinish(page);

  const table = page.getByTestId("comparison");
  await expect(table).toBeVisible();
  await expect(table.getByRole("row", { name: /Screens/ })).toContainText("25");
  await expect(table.getByRole("row", { name: /Screens/ })).toContainText("22");
  // The test taps the first option on each screen, so it uses no suggestions: 5 facts come from Health.
  await expect(table.getByRole("row", { name: /From Apple Health/ })).toContainText("5");
  await expect(page.getByTestId("from-health")).toContainText("5 answers filled for you.");
  await expect(page.getByText(/second run is always faster/)).toBeVisible();
});

test("the dietitian view shows the summary and where each answer came from", async ({ page }) => {
  await startOnboarding(page, "A", "Health first");
  await runToFinish(page);

  await page.getByRole("button", { name: "See what the dietitian gets" }).click();

  const view = page.getByTestId("dietitian");
  await expect(view.getByTestId("summary-text")).toContainText("Offline stand-in summary");
  await expect(view.getByTestId("summary-text")).toContainText("162 lb (73.4 kg)");
  await expect(view.getByTestId("summary-text")).not.toContainText("{{");
  await expect(view.getByText(/filled in by code afterwards/)).toBeVisible();
  await expect(view.getByText(/Written by the offline stand-in, not a model/)).toBeVisible();
  await expect(view.locator('[data-answer="weight"]')).toContainText("From Health, confirmed");
  await expect(view.locator('[data-answer="main_goal"]')).toContainText("Entered by member");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);
});

test("reopening the dietitian view reuses the summary", async ({ page }) => {
  await startOnboarding(page, "C", "Today's order");
  await runToFinish(page);
  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/summary")) calls.push(r.url());
  });

  await page.getByRole("button", { name: "See what the dietitian gets" }).click();
  await expect(page.getByTestId("summary-text")).toBeVisible();
  await page.getByRole("button", { name: "Back" }).last().click();
  await page.getByRole("button", { name: "See what the dietitian gets" }).click();
  await expect(page.getByTestId("summary-text")).toBeVisible();

  const egress = await page.evaluate(async () => {
    const id = JSON.parse(localStorage.getItem("intake-demo-session")!).id;
    const api = "http://localhost:8100";
    return (await (await fetch(`${api}/sessions/${id}/egress`)).json()) as { purpose: string }[];
  });
  expect(calls).toHaveLength(2);
  expect(egress.filter((e) => e.purpose === "dietitian_summary")).toHaveLength(1);
});
