import { test, expect } from "@playwright/test";

test.describe("Навигация", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("главная страница загружается", async ({ page }) => {
    await expect(page).toHaveTitle(/Survey/i);
    await expect(page.locator("body")).toBeVisible();
  });

  test("сайдбар отображается с ссылками", async ({ page }) => {
    const sidebar = page.locator("nav, [data-sidebar]");
    await expect(sidebar.first()).toBeVisible();
  });

  test("тёмная тема активна по умолчанию", async ({ page }) => {
    const html = page.locator("html");
    await expect(html).toHaveClass(/dark/);
  });

  test("навигация по страницам проекта работает", async ({ page }) => {
    // Создаём или переходим в проект
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (await projectLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await projectLink.click();
      await page.waitForURL(/\/projects\//);

      // Проверяем навигационные ссылки в сайдбаре проекта
      const navLinks = page.locator("a[href*='/projects/']");
      await expect(navLinks.first()).toBeVisible();
    }
  });

  test("кнопка назад в браузере работает", async ({ page }) => {
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (await projectLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      const initialUrl = page.url();
      await projectLink.click();
      await page.waitForURL(/\/projects\//);
      await page.goBack();
      await expect(page).toHaveURL(initialUrl);
    }
  });
});
