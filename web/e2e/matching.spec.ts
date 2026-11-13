import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { answerUntil, currentScreen, startOnboarding } from "./flow";

// The end-to-end API runs with LLM_TRANSPORT=offline: a keyword matcher stands in for Claude.

test("a concern in the member's own words gives matches to pick from", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "health_concern");

  await page.getByLabel("In your own words").fill("my kidney stones came back");
  await page.getByRole("button", { name: "Find matches" }).click();

  const match = page.getByRole("radio", { name: "Kidney stones" });
  await expect(match).toBeVisible();
  await expect(match).not.toBeChecked();
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);
  await match.check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("eating_barriers");
});

test("no match falls back to the full list", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "health_concern");

  await page.getByLabel("In your own words").fill("my left knee aches");
  await page.getByRole("button", { name: "Find matches" }).click();

  await expect(page.getByRole("status")).toContainText("couldn't match that");
  await expect(page.getByRole("searchbox", { name: "Filter conditions" })).toBeVisible();
});

test("a Something else answer can be swapped for a matching option", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "allergies");

  await page.getByRole("checkbox", { name: "Something else" }).check();
  await page.getByLabel("Something else: tell us more").fill("lactose upsets my stomach");
  await page.getByRole("button", { name: "Check the list for a match" }).click();
  await page.getByRole("button", { name: "Use “Dairy or lactose”" }).click();

  await expect(page.getByRole("checkbox", { name: "Dairy or lactose" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Something else" })).not.toBeChecked();
});

test("the model call appears in Behind the scenes", async ({ page, isMobile }) => {
  test.skip(isMobile, "the panel is beside the app on wide screens");
  await startOnboarding(page);
  await answerUntil(page, "health_concern");

  await page.getByLabel("In your own words").fill("heartburn after dinner, acid reflux");
  await page.getByRole("button", { name: "Find matches" }).click();
  await expect(page.getByRole("radio", { name: "Acid reflux or GERD" })).toBeVisible();
  await page.getByRole("radio", { name: "Acid reflux or GERD" }).check();
  await page.getByRole("button", { name: "Continue" }).click();

  const panel = page.getByRole("complementary", { name: "Behind the scenes" });
  await panel.getByText("condition_match · ok").click();
  await expect(panel.locator("pre").first()).toContainText("<member_text>heartburn after dinner, acid reflux</member_text>");
});
