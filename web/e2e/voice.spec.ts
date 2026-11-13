import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { answerUntil, currentScreen, startOnboarding } from "./flow";

// The end-to-end API runs with LLM_TRANSPORT=offline: a keyword matcher stands in for Claude.

test("the simulated mic fills several answers from one spoken reply", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "voice_goals");

  await expect(page.getByText("Simulated: voice")).toBeVisible();
  await page.getByRole("button", { name: "Speak (simulated)" }).click();
  await expect(page.getByRole("status")).toContainText("Listening");
  await expect(page.getByLabel("What you said")).toHaveValue(/prediabetes/, { timeout: 15_000 });

  const heard = page.getByRole("region", { name: "From what you said" });
  await expect(heard).toBeVisible();
  await expect(page.locator('[data-voice-row="main_goal"]')).toContainText("More energy");
  await expect(page.locator('[data-voice-row="meals_per_day"]')).toContainText("Three times");
  await expect(page.locator('[data-voice-row="health_concern"]')).toContainText("Prediabetes");
  await expect(page.locator('[data-voice-row="weight_goal"]')).toContainText("Not mentioned");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);

  // A matched condition is a suggestion, and an unmentioned question still needs a choice.
  const confirm = page.getByRole("button", { name: "Check highlighted answers" });
  await expect(confirm).toBeDisabled();
  await page.getByRole("button", { name: "Looks right" }).click();
  await page.getByRole("button", { name: "Choose Weight goal" }).click();
  await page.getByRole("radio", { name: "Stay where I am" }).check();
  await page.getByRole("button", { name: "Use this" }).click();
  await page.getByRole("button", { name: "Confirm" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe("voice_food");
});

test("the member can type their own words instead", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "voice_food");

  await page.getByLabel("What you said").fill("I'm vegan and I can't eat peanuts.");
  await page.getByRole("button", { name: "Fill in my answers" }).click();

  await expect(page.locator('[data-voice-row="diet_pattern"]')).toContainText("Vegan");
  await expect(page.locator('[data-voice-row="allergies"]')).toContainText("Peanuts");
  await expect(page.locator('[data-voice-row="cuisines"]')).toContainText("Not mentioned");
});

test("each answer can be chosen by hand without speaking", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "voice_kitchen");

  await page.getByRole("button", { name: "Answer each one instead" }).click();

  await expect(page.getByRole("button", { name: /^Choose / })).toHaveCount(4);
  await expect(page.getByRole("button", { name: /^Add / })).toHaveCount(2);
});

test("the extraction request appears in Behind the scenes", async ({ page, isMobile }) => {
  test.skip(isMobile, "the panel is beside the app on wide screens");
  await startOnboarding(page);
  await answerUntil(page, "voice_food");

  await page.getByLabel("What you said").fill("I'm vegetarian.");
  await page.getByRole("button", { name: "Fill in my answers" }).click();
  await expect(page.locator('[data-voice-row="diet_pattern"]')).toContainText("Vegetarian");
  while ((await page.getByRole("button", { name: /^Choose / }).count()) > 0) {
    await page.getByRole("button", { name: /^Choose / }).first().click();
    await page.locator("[data-screen-id] label").first().click();
    await page.getByRole("button", { name: "Use this" }).click();
  }
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("voice_kitchen");

  const panel = page.getByRole("complementary", { name: "Behind the scenes" });
  await panel.getByText("voice_extract · ok").last().click();
  await expect(panel.locator("details[open] pre").first()).toContainText("<member_text>I'm vegetarian.</member_text>");
});
