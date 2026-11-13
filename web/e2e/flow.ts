import { expect, type Page } from "@playwright/test";

export async function startOnboarding(page: Page, member: "A" | "B" | "C", order: "Today's order" | "Health first") {
  await page.goto("/");
  await page.getByRole("radio", { name: new RegExp(`^${member}:`) }).check();
  await page.getByRole("radio", { name: new RegExp(order) }).check();
  await page.getByRole("button", { name: "Start onboarding" }).click();
  await expect(page.locator("[data-screen-id]")).toBeVisible();
}

export async function currentScreen(page: Page): Promise<{ id: string; kind: string }> {
  const screen = page.locator("[data-screen-id]");
  return { id: (await screen.getAttribute("data-screen-id"))!, kind: (await screen.getAttribute("data-kind"))! };
}

/** Answer whatever screen is showing with a valid default, the way a member tapping through would. */
export async function answerCurrent(page: Page): Promise<string> {
  const { id, kind } = await currentScreen(page);
  const screen = page.locator(`[data-screen-id="${id}"]`);
  switch (kind) {
    case "single_choice":
    case "multi_choice":
      await screen.locator("label").first().click();
      break;
    case "date":
      await screen.getByLabel("Month").selectOption("6");
      await screen.getByLabel("Day").selectOption("15");
      await screen.getByLabel("Year").selectOption("1990");
      break;
    case "height":
      await screen.getByLabel("Feet", { exact: true }).fill("5");
      await screen.getByLabel("Inches", { exact: true }).fill("9");
      break;
    case "weight":
      await screen.getByRole("spinbutton").fill("160");
      break;
    case "text":
      await screen.getByRole("textbox").fill("None");
      break;
    case "condition_picker":
      await screen.getByText("No specific condition").click();
      break;
    case "health_review":
      for (const button of await screen.getByRole("button", { name: "Looks right" }).all()) await button.click();
      break;
  }
  const action = kind === "health_permission" ? "Allow" : kind === "health_review" ? "Confirm" : "Continue";
  await screen.getByRole("button", { name: action, exact: true }).click();
  await expect(page.locator(`[data-screen-id="${id}"]`)).toHaveCount(0);
  return id;
}

/** Answer screens until the finish screen, returning the ids visited. */
export async function runToFinish(page: Page): Promise<string[]> {
  const visited: string[] = [];
  while (!(await page.getByTestId("finish").isVisible())) {
    visited.push(await answerCurrent(page));
    if (visited.length > 40) throw new Error("flow did not finish");
  }
  return visited;
}
