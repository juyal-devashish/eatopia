import { expect, test } from "@playwright/test";

import { answerCurrent, currentScreen, runToFinish, startOnboarding } from "./flow";

for (const member of ["A", "B", "C"] as const) {
  test(`member ${member} completes today's order`, async ({ page }) => {
    await startOnboarding(page, member, "Today's order");

    const visited = await runToFinish(page);

    expect(visited).toHaveLength(25);
    expect(visited.indexOf("health_permission_late")).toBeGreaterThan(visited.indexOf("exercise_frequency"));
    await expect(page.getByTestId("screens-seen")).toHaveText("25");
  });
}

test("Back shows the earlier answer and a new answer replaces it", async ({ page }) => {
  await startOnboarding(page, "A", "Today's order");
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
  await startOnboarding(page, "B", "Today's order");
  await answerCurrent(page);
  await answerCurrent(page);
  const before = await currentScreen(page);

  await page.reload();
  await page.getByRole("button", { name: "Continue where you left off" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe(before.id);
});

test("weight can be skipped", async ({ page }) => {
  await startOnboarding(page, "C", "Today's order");
  while ((await currentScreen(page)).id !== "weight") await answerCurrent(page);

  await page.getByRole("button", { name: "Add this later" }).click();

  await expect.poll(async () => (await currentScreen(page)).id).toBe("weight_goal");
});

test("after a reload, Back still reaches earlier answers", async ({ page }) => {
  await startOnboarding(page, "A", "Today's order");
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
