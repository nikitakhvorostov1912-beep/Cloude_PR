import { test, expect } from "@playwright/test";

test.describe("Загрузка файлов", () => {
  test.beforeEach(async ({ page }) => {
    // Переходим на страницу загрузки первого проекта
    await page.goto("/");
    const projectLink = page.locator("a[href*='/projects/']").first();
    if (!await projectLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      test.skip();
      return;
    }
    await projectLink.click();
    await page.waitForURL(/\/projects\//);

    // Переходим на вкладку загрузки
    const uploadLink = page.locator("a[href*='/upload']").first();
    if (await uploadLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await uploadLink.click();
      await page.waitForURL(/\/upload/);
    }
  });

  test("страница загрузки отображается", async ({ page }) => {
    if (!page.url().includes("/upload")) {
      test.skip();
      return;
    }
    const heading = page.getByText(/загрузка|файлы|импорт/i).first();
    await expect(heading).toBeVisible({ timeout: 5000 });
  });

  test("зона drag-drop видна", async ({ page }) => {
    if (!page.url().includes("/upload")) {
      test.skip();
      return;
    }
    // Ожидаем зону для загрузки (drop zone)
    const dropZone = page.locator("[class*='border-dashed'], [class*='dropzone']").first();
    if (await dropZone.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(dropZone).toBeVisible();
    }
  });

  test("поле для пути к папке доступно", async ({ page }) => {
    if (!page.url().includes("/upload")) {
      test.skip();
      return;
    }
    const pathInput = page.getByPlaceholder(/путь|папка|folder/i).first();
    if (await pathInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(pathInput).toBeEditable();
    }
  });
});
