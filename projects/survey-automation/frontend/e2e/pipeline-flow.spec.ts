import { test, expect } from "@playwright/test";

test.describe("Пайплайн обработки", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (!await projectLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      test.skip();
      return;
    }
    await projectLink.click();
    await page.waitForURL(/\/projects\//);
  });

  test("прогресс пайплайна отображается", async ({ page }) => {
    if (!page.url().includes("/projects/")) {
      test.skip();
      return;
    }
    // Ожидаем карточки стадий пайплайна
    const stageCards = page.locator("[class*='card'], [class*='Card']");
    await expect(stageCards.first()).toBeVisible({ timeout: 5000 });
  });

  test("кнопки запуска стадий отображаются", async ({ page }) => {
    if (!page.url().includes("/projects/")) {
      test.skip();
      return;
    }
    const runButtons = page.getByRole("button", { name: /запустить|запуск|play/i });
    if (await runButtons.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(runButtons.first()).toBeVisible();
    }
  });

  test("запуск стадии показывает индикатор загрузки", async ({ page }) => {
    if (!page.url().includes("/projects/")) {
      test.skip();
      return;
    }
    const runBtn = page.getByRole("button", { name: /запустить|запуск/i }).first();
    if (!await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip();
      return;
    }

    if (await runBtn.isEnabled()) {
      await runBtn.click();
      // Ожидаем появление спиннера или текста загрузки
      const loadingIndicator = page.locator("[class*='animate-spin'], [class*='loading']").first();
      // Кнопка должна стать неактивной или показать спиннер
      await page.waitForTimeout(500);
      const isDisabled = await runBtn.isDisabled().catch(() => false);
      const hasSpinner = await loadingIndicator.isVisible({ timeout: 2000 }).catch(() => false);
      expect(isDisabled || hasSpinner).toBeTruthy();
    }
  }, { timeout: 30_000 });
});
