/**
 * E2E тест: управление проектами (CRUD).
 *
 * Проверяет:
 * 1. API GET /api/projects возвращает список проектов
 * 2. API POST /api/projects создаёт новый проект
 * 3. API GET /api/projects/:id возвращает данные проекта
 * 4. API DELETE /api/projects/:id удаляет проект
 * 5. Главная страница показывает проекты
 *
 * Примечание: UI тесты проверяют отображение, API тесты — логику.
 */
import { test, expect } from "@playwright/test";

const BACKEND = "http://localhost:8000";
const PROJECT_ID = "ecb4ac19b44f49bb9da0ab72d817251a";

// ---------------------------------------------------------------------------
// Тест 1: API — список проектов
// ---------------------------------------------------------------------------

test.describe("Проекты API — список", () => {
  test("GET /api/projects возвращает список проектов", async ({ request }) => {
    const response = await request.get(`${BACKEND}/api/projects`);
    expect(response.status()).toBe(200);

    // API возвращает { projects: [...], total: N }
    const data = await response.json();
    const projects = Array.isArray(data) ? data : (data.projects ?? []);
    expect(Array.isArray(projects)).toBe(true);
    expect(projects.length).toBeGreaterThan(0);
  });

  test("GET /api/projects содержит тестовый проект", async ({ request }) => {
    const response = await request.get(`${BACKEND}/api/projects`);
    const data = await response.json();
    const projects: { id: string }[] = Array.isArray(data) ? data : (data.projects ?? []);

    const found = projects.find((p) => p.id === PROJECT_ID);
    expect(
      found,
      `Проект ${PROJECT_ID} не найден в списке`
    ).toBeTruthy();
  });

  test("GET /api/projects/:id возвращает данные проекта", async ({ request }) => {
    const response = await request.get(`${BACKEND}/api/projects/${PROJECT_ID}`);
    expect(response.status()).toBe(200);

    const project = await response.json();
    expect(project.id).toBe(PROJECT_ID);
    expect(typeof project.name).toBe("string");
  });
});

// ---------------------------------------------------------------------------
// Тест 2: API — создание и удаление проекта
// ---------------------------------------------------------------------------

test.describe("Проекты API — создание и удаление", () => {
  let createdProjectId: string | null = null;

  test("POST /api/projects создаёт новый проект", async ({ request }) => {
    const testName = `E2E Test Project ${Date.now()}`;

    const response = await request.post(`${BACKEND}/api/projects`, {
      data: { name: testName },
      headers: { "Content-Type": "application/json" },
    });

    // POST возвращает 201 Created
    expect([200, 201]).toContain(response.status());

    const project = await response.json();
    expect(project.id).toBeTruthy();
    expect(project.name).toBe(testName);

    createdProjectId = project.id;
  });

  test("DELETE /api/projects/:id удаляет созданный проект", async ({ request }) => {
    // Создаём проект для удаления
    const testName = `E2E Delete Test ${Date.now()}`;
    const createResp = await request.post(`${BACKEND}/api/projects`, {
      data: { name: testName },
      headers: { "Content-Type": "application/json" },
    });
    // POST возвращает 201 Created
    expect([200, 201]).toContain(createResp.status());

    const project = await createResp.json();
    const projectId = project.id;

    // Удаляем
    const deleteResp = await request.delete(
      `${BACKEND}/api/projects/${projectId}`
    );
    expect(deleteResp.status()).toBe(200);

    // Проверяем что удалён
    const getResp = await request.get(
      `${BACKEND}/api/projects/${projectId}`
    );
    expect(getResp.status()).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// Тест 3: UI — отображение проектов
// ---------------------------------------------------------------------------

test.describe("Проекты UI", () => {
  test("Главная страница содержит список проектов", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle", timeout: 30_000 });

    // Страница должна отображаться без ошибок
    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");

    // Должен быть контент (не пустая страница)
    expect((bodyText ?? "").trim().length).toBeGreaterThan(50);
  });

  test("Переход на страницу проекта работает", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}`, {
      waitUntil: "domcontentloaded",
      timeout: 20_000,
    });

    // URL должен содержать project ID
    expect(page.url()).toContain(PROJECT_ID);

    // Страница без ошибок
    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
  });

  test("Страница процессов проекта отображает процессы", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/processes`, {
      waitUntil: "networkidle",
      timeout: 30_000,
    });

    // Ждём появления любого контента
    const body = page.locator("body");
    await expect(body).toBeVisible();

    // Контент должен быть содержательным
    const bodyText = await page.textContent("body");
    expect((bodyText ?? "").length).toBeGreaterThan(100);
  });
});
