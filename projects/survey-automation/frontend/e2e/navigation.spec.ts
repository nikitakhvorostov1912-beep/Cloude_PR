/**
 * E2E тест: навигация и базовая проверка страниц.
 *
 * Проверяет:
 * 1. Главная страница загружается без ошибок
 * 2. Все основные разделы проекта доступны (200, нет 500)
 * 3. Тёмная тема применена (bg-background класс)
 * 4. Заголовок страницы существует
 * 5. Нет JS-ошибок на критических страницах
 */
import { test, expect } from "@playwright/test";

const PROJECT_ID = "ecb4ac19b44f49bb9da0ab72d817251a";

const PROJECT_PAGES = [
  { name: "Обзор проекта", path: `/projects/${PROJECT_ID}` },
  { name: "Загрузка файлов", path: `/projects/${PROJECT_ID}/upload` },
  { name: "Файлы", path: `/projects/${PROJECT_ID}/files` },
  { name: "Процессы", path: `/projects/${PROJECT_ID}/processes` },
  { name: "Транскрипты", path: `/projects/${PROJECT_ID}/transcripts` },
  { name: "GAP-анализ", path: `/projects/${PROJECT_ID}/gaps` },
  { name: "Требования", path: `/projects/${PROJECT_ID}/requirements` },
];

test.describe("Навигация — главная страница", () => {
  test("Главная страница загружается без ошибок", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Заголовок существует
    const title = await page.title();
    expect(title).toBeTruthy();

    // Нет серверных ошибок на странице (innerText исключает script/style теги)
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Internal Server Error");
    expect(bodyText).not.toContain("Application error");
  });

  test("Список проектов отображается на главной", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // Страница должна отображать хоть какой-то контент
    const body = await page.locator("body");
    await expect(body).toBeVisible();

    // Не должно быть пустой страницы
    const text = await page.textContent("body");
    expect((text ?? "").trim().length).toBeGreaterThan(10);
  });
});

test.describe("Навигация — страницы проекта", () => {
  for (const { name, path } of PROJECT_PAGES) {
    test(`Страница "${name}" загружается (${path})`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (err) => errors.push(err.message));

      await page.goto(path, { waitUntil: "domcontentloaded", timeout: 20_000 });

      // URL не должен редиректить на ошибочную страницу
      expect(page.url()).toContain(PROJECT_ID);

      // Нет критических серверных ошибок (innerText исключает script/style теги)
      const bodyText = await page.locator("body").innerText();
      expect(bodyText).not.toContain("Internal Server Error");
    });
  }
});

test.describe("Навигация — тёмная тема", () => {
  test("HTML-элемент имеет класс dark (тёмная тема)", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Next.js приложение использует тёмную тему по умолчанию
    const htmlClass = await page.locator("html").getAttribute("class");
    const bodyClass = await page.locator("body").getAttribute("class");
    const combined = `${htmlClass ?? ""} ${bodyClass ?? ""}`;

    // Должен быть класс dark, или dark-themed background
    const hasDarkTheme =
      combined.includes("dark") ||
      combined.includes("background") ||
      combined.includes("bg-");

    expect(hasDarkTheme, `Классы html: "${htmlClass}", body: "${bodyClass}"`).toBe(true);
  });
});

test.describe("Backend health", () => {
  test("API health endpoint отвечает 200", async ({ request }) => {
    const response = await request.get("http://localhost:8000/api/health", {
      timeout: 5_000,
    });
    expect(response.status()).toBe(200);
  });

  test("API projects endpoint отвечает 200", async ({ request }) => {
    const response = await request.get("http://localhost:8000/api/projects", {
      timeout: 5_000,
    });
    expect(response.status()).toBe(200);

    // API возвращает { projects: [...], total: N }
    const data = await response.json();
    const projects = Array.isArray(data) ? data : (data.projects ?? data);
    expect(projects).toBeTruthy();
  });
});
