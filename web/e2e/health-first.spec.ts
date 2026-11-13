import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { answerCurrent, currentScreen, runToFinish, startOnboarding } from "./flow";

const FACTS = ["sex_at_birth", "date_of_birth", "height", "weight", "steps"];

async function answerUntil(page: Page, screenId: string) {
  while ((await currentScreen(page)).id !== screenId) await answerCurrent(page);
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

test("member A reviews five facts on one card and skips those questions", async ({ page }) => {
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "health_review");

  await expect(page.locator("[data-row]")).toHaveCount(5);
  await expectAccessible(page);
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("gender_identity");
  const visited = ["health_review", ...(await runToFinish(page))];

  expect(visited.filter((id) => FACTS.includes(id))).toEqual([]);
  await expect(page.getByTestId("screens-answered")).toHaveText("27");
});

test("estimates are highlighted, never preselected", async ({ page }) => {
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "exercise_frequency");

  const suggested = page.getByRole("radio", { name: /5 to 6 days/ });
  await expect(page.getByText("Suggested", { exact: true })).toBeVisible();
  await expect(suggested).not.toBeChecked();
  await expect(page.getByText(/Suggested from Apple Health: 22 workouts/)).toBeVisible();
  await expectAccessible(page);
});

test("member B reviews only usable facts and is asked the rest", async ({ page }) => {
  await startOnboarding(page, "B", "Health first");
  await answerUntil(page, "health_review");

  await expect(page.locator("[data-row]")).toHaveCount(3);
  await answerCurrent(page);
  await answerUntil(page, "weight");
  await expect(page.getByText(/couldn't answer this. Latest weight in Apple Health is 120 days old/)).toBeVisible();
});

test("member C has nothing to review", async ({ page }) => {
  await startOnboarding(page, "C", "Health first");
  const visited = await runToFinish(page);

  expect(visited).not.toContain("health_review");
  expect(visited).toEqual(expect.arrayContaining(FACTS));
});

test("denying access asks every question", async ({ page }) => {
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "health_permission_early");
  await page.getByRole("button", { name: "Don't allow" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe("gender_identity");
  await answerCurrent(page);
  await expect.poll(async () => (await currentScreen(page)).id).toBe("sex_at_birth");
});

test("a row with weak data needs its own tap before Confirm", async ({ page }) => {
  // Make member A's weight look 45 days old: the rule then flags it for a check.
  await page.route("**/sessions/**", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    if (body?.suggestions?.weight) {
      body.suggestions.weight.status = "needs_check";
      body.suggestions.weight.evidence = "Latest weight in Apple Health, 45 days ago";
    }
    await route.fulfill({ response, json: body });
  });
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "health_review");

  const confirm = page.getByRole("button", { name: "Check the highlighted answer" });
  await expect(confirm).toBeDisabled();
  await page.getByRole("button", { name: "Looks right" }).click();
  await expect(page.getByRole("button", { name: "Confirm" })).toBeEnabled();
});

test("changing a row records it as changed", async ({ page, isMobile }) => {
  test.skip(isMobile, "the panel is beside the app on wide screens");
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "health_review");

  await page.getByRole("button", { name: "Change Daily steps" }).click();
  await page.getByRole("radio", { name: "12,000 or more" }).check();
  await page.getByRole("button", { name: "Use this" }).click();
  await expect(page.locator('[data-row="steps"]')).toContainText("Changed by you");
  await page.getByRole("button", { name: "Confirm" }).click();

  const panel = page.getByRole("complementary", { name: "Behind the scenes" });
  await expect(panel.getByText("from Health, changed")).toBeVisible();
  await expect(panel.getByText("from Health, confirmed").first()).toBeVisible();
});

test("the panel opens from Details on a phone", async ({ page, isMobile }) => {
  test.skip(!isMobile, "phones show the panel behind a button");
  await startOnboarding(page, "A", "Health first");
  await answerUntil(page, "health_review");

  await page.getByRole("button", { name: "Details" }).click();

  await expect(page.getByRole("heading", { name: "Behind the scenes" }).filter({ visible: true })).toBeVisible();
  await expect(page.getByText("What each rule did").filter({ visible: true })).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("button", { name: "Back to onboarding" }).click();
  await expect(page.locator("[data-row]")).toHaveCount(5);
});

test("the start screen is accessible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Start onboarding" })).toBeEnabled();
  await expectAccessible(page);
});
