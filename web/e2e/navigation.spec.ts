import { expect, test } from "@playwright/test";

import { answerCurrent, answerUntil, currentScreen, startOnboarding } from "./flow";

test("Back shows the earlier answer and a new answer replaces it", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "gender_identity");
  await page.getByRole("radio", { name: "Woman" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("voice_goals");

  await page.getByRole("button", { name: "Back" }).click();

  await expect(page.getByRole("radio", { name: "Woman" })).toBeChecked();
  await page.getByRole("radio", { name: "Nonbinary" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("voice_goals");
});

test("Back to a voice screen shows the answers already confirmed", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "voice_food");

  await page.getByRole("button", { name: "Back" }).click();

  await expect(page.locator('[data-voice-row="main_goal"]')).toContainText("More energy");
  await expect(page.getByRole("button", { name: "Confirm" })).toBeEnabled();
});

test("a reloaded page offers to resume at the same screen", async ({ page }) => {
  await startOnboarding(page);
  await answerCurrent(page);
  await answerCurrent(page);
  const before = await currentScreen(page);

  await page.reload();
  await page.getByRole("button", { name: "Continue where you left off" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe(before.id);
});

test("weight can be skipped when Health access is denied", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "health_permission_early");
  await page.getByRole("button", { name: "Don't allow" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("gender_identity");
  await answerUntil(page, "weight");

  await page.getByRole("button", { name: "Add this later" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe("exercise_frequency");
});

test("after a reload, Back still reaches earlier answers", async ({ page }) => {
  await startOnboarding(page);
  await answerUntil(page, "gender_identity");
  await page.getByRole("radio", { name: "Woman" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("voice_goals");

  await page.reload();
  await page.getByRole("button", { name: "Continue where you left off" }).click();
  await page.getByRole("button", { name: "Back" }).click();

  await expect(page.getByRole("radio", { name: "Woman" })).toBeChecked();
});
