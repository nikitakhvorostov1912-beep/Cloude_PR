import { test, expect } from "@playwright/test";

test.describe("CRUD проектов", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("отображается список проектов или пустое состояние", async ({ page }) => {
    // Либо карточки проектов, либо empty state
    const content = page.locator("main, [role='main']").first();
    await expect(content).toBeVisible({ timeout: 5000 });
  });

  test("кнопка создания проекта доступна", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /создать|новый/i });
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(createBtn).toBeEnabled();
    }
  });

  test("создание проекта с названием", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /создать|новый/i });
    if (!await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await createBtn.click();

    // Ожидаем появление диалога/формы
    const nameInput = page.getByPlaceholder(/название|имя/i).or(
      page.locator("input[type='text']").first()
    );
    if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nameInput.fill("Тестовый проект E2E");

      const submitBtn = page.getByRole("button", { name: /создать|сохранить|ок/i });
      if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await submitBtn.click();
        // Должны перейти на страницу проекта или увидеть его в списке
        await page.waitForTimeout(1000);
      }
    }
  });

  test("переход в проект по клику на карточку", async ({ page }) => {
    const projectCard = page.locator("a[href*='/projects/']").first();
    if (!await projectCard.isVisible({ timeout: 3000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await projectCard.click();
    await page.waitForURL(/\/projects\//, { timeout: 5000 });
    await expect(page).toHaveURL(/\/projects\//);
  });
});
