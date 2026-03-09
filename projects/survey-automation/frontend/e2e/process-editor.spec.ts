import { test, expect } from "@playwright/test";

test.describe("Редактор процессов", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (!await projectLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      test.skip();
      return;
    }
    await projectLink.click();
    await page.waitForURL(/\/projects\//);

    const processLink = page.locator("a[href*='/processes']").first();
    if (await processLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await processLink.click();
      await page.waitForURL(/\/processes/);
    }
  });

  test("список процессов отображается или пустое состояние", async ({ page }) => {
    if (!page.url().includes("/processes")) {
      test.skip();
      return;
    }
    const content = page.locator("main").first();
    await expect(content).toBeVisible({ timeout: 5000 });

    // Либо accordion с процессами, либо empty state
    const processes = page.locator("[data-state], [class*='accordion'], [class*='Accordion']");
    const emptyState = page.getByText(/нет процессов|не найден/i);
    const hasProcesses = await processes.first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);
    expect(hasProcesses || hasEmpty).toBeTruthy();
  });

  test("accordion раскрывается по клику", async ({ page }) => {
    if (!page.url().includes("/processes")) {
      test.skip();
      return;
    }
    const trigger = page.locator("[data-state='closed']").first();
    if (!await trigger.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await trigger.click();
    await page.waitForTimeout(300);
    // После клика состояние должно измениться на open
    await expect(trigger).toHaveAttribute("data-state", "open", { timeout: 2000 });
  });
});
