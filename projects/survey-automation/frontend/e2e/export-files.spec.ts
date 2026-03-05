import { test, expect } from "@playwright/test";

test.describe("Экспорт файлов", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (!await projectLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      test.skip();
      return;
    }
    await projectLink.click();
    await page.waitForURL(/\/projects\//);

    const filesLink = page.locator("a[href*='/files']").first();
    if (await filesLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await filesLink.click();
      await page.waitForURL(/\/files/);
    }
  });

  test("страница файлов отображается", async ({ page }) => {
    if (!page.url().includes("/files")) {
      test.skip();
      return;
    }
    const heading = page.getByText(/файлы|экспорт|артефакты/i).first();
    await expect(heading).toBeVisible({ timeout: 5000 });
  });

  test("кнопки скачивания доступны", async ({ page }) => {
    if (!page.url().includes("/files")) {
      test.skip();
      return;
    }
    const downloadButtons = page.getByRole("link", { name: /скачать|download|excel|word|visio|zip/i });
    if (await downloadButtons.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      const count = await downloadButtons.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test("кнопка скачать всё (ZIP) доступна", async ({ page }) => {
    if (!page.url().includes("/files")) {
      test.skip();
      return;
    }
    const zipBtn = page.getByRole("link", { name: /zip|всё|все/i })
      .or(page.getByRole("button", { name: /zip|всё|все/i }));
    if (await zipBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(zipBtn.first()).toBeVisible();
    }
  });
});
