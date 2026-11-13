import { expect, test } from "@playwright/test";

import { answerCurrent, answerUntil, currentScreen, startOnboarding } from "./flow";

test("Back shows the earlier answer and a new answer replaces it", async ({ page }) => {
  await startOnboarding(page);
  await page.getByRole("radio", { name: "More energy" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("dietitian_note");

  await page.getByRole("button", { name: "Back" }).click();

  await expect(page.getByRole("radio", { name: "More energy" })).toBeChecked();
  await page.getByRole("radio", { name: "Better digestion" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("dietitian_note");
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

  await expect.poll(async () => (await currentScreen(page)).id).toBe("weight_goal");
});

test("after a reload, Back still reaches earlier answers", async ({ page }) => {
  await startOnboarding(page);
  await page.getByRole("radio", { name: "More energy" }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect.poll(async () => (await currentScreen(page)).id).toBe("dietitian_note");
  await answerCurrent(page);

  await page.reload();
  await page.getByRole("button", { name: "Continue where you left off" }).click();
  await page.getByRole("button", { name: "Back" }).click();
  await page.getByRole("button", { name: "Back" }).click();

  await expect(page.getByRole("radio", { name: "More energy" })).toBeChecked();
});
