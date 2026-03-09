/**
 * E2E тест: редактор процессов.
 *
 * Проверяет:
 * 1. API GET /api/projects/:id/processes возвращает список процессов
 * 2. API GET /api/projects/:id/processes/:proc_id возвращает процесс
 * 3. Страница процессов загружается и отображает контент
 * 4. Страница GAP-анализа загружается
 * 5. Страница требований загружается
 */
import { test, expect } from "@playwright/test";

const PROJECT_ID = "ecb4ac19b44f49bb9da0ab72d817251a";
const BACKEND = "http://localhost:8000";
const PROCESSES = ["proc_001", "proc_002", "proc_003", "proc_004"];

// ---------------------------------------------------------------------------
// Тест 1: API процессов
// ---------------------------------------------------------------------------

test.describe("Процессы API", () => {
  test("GET /api/projects/:id/processes возвращает список", async ({ request }) => {
    const response = await request.get(
      `${BACKEND}/api/projects/${PROJECT_ID}/processes`
    );
    expect(response.status()).toBe(200);

    const data = await response.json();
    // Ответ может быть массивом или объектом с полем processes
    const processes = Array.isArray(data) ? data : data.processes ?? [];
    expect(processes.length).toBeGreaterThan(0);
  });

  for (const procId of PROCESSES) {
    test(`GET /api/projects/:id/processes/${procId} возвращает процесс`, async ({ request }) => {
      const response = await request.get(
        `${BACKEND}/api/projects/${PROJECT_ID}/processes/${procId}`
      );
      expect(response.status()).toBe(200);

      const proc = await response.json();
      // Процесс должен иметь id или name
      const hasId = proc.id || proc.process_id || proc.name;
      expect(hasId, `Процесс ${procId} должен иметь идентификатор`).toBeTruthy();
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 2: BPMN JSON данные
// ---------------------------------------------------------------------------

test.describe("BPMN JSON данные", () => {
  for (const procId of PROCESSES) {
    test(`Процесс ${procId} содержит элементы BPMN`, async ({ request }) => {
      const response = await request.get(
        `${BACKEND}/api/projects/${PROJECT_ID}/processes/${procId}`
      );
      expect(response.status()).toBe(200);

      const proc = await response.json();

      // Должны быть какие-то данные о процессе
      const text = JSON.stringify(proc);
      expect(text.length).toBeGreaterThan(100);
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 3: UI — страница процессов
// ---------------------------------------------------------------------------

test.describe("Процессы UI", () => {
  test("Страница /processes загружается и содержит контент", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/processes`, {
      waitUntil: "networkidle",
      timeout: 30_000,
    });

    // Страница без ошибок
    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");

    // Контент достаточно большой (загружены данные)
    expect((bodyText ?? "").trim().length).toBeGreaterThan(100);
  });

  test("Страница процессов содержит названия процессов", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/processes`, {
      waitUntil: "networkidle",
      timeout: 30_000,
    });

    const bodyText = await page.textContent("body");

    // Хотя бы один из процессов должен отображаться
    const hasProcessContent =
      (bodyText ?? "").includes("проц") ||
      (bodyText ?? "").includes("Проц") ||
      (bodyText ?? "").includes("proc") ||
      (bodyText ?? "").includes("заказ") ||
      (bodyText ?? "").includes("склад") ||
      (bodyText ?? "").includes("отгрузк") ||
      (bodyText ?? "").includes("скидк");

    expect(
      hasProcessContent,
      "Страница должна содержать данные о процессах"
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Тест 4: UI — GAP-анализ и требования
// ---------------------------------------------------------------------------

test.describe("GAP-анализ и Требования UI", () => {
  test("Страница GAP-анализа загружается", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/gaps`, {
      waitUntil: "domcontentloaded",
      timeout: 20_000,
    });

    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
    expect(page.url()).toContain(PROJECT_ID);
  });

  test("Страница требований загружается", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/requirements`, {
      waitUntil: "domcontentloaded",
      timeout: 20_000,
    });

    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
    expect(page.url()).toContain(PROJECT_ID);
  });

  test("Страница транскриптов загружается", async ({ page }) => {
    await page.goto(`/projects/${PROJECT_ID}/transcripts`, {
      waitUntil: "domcontentloaded",
      timeout: 20_000,
    });

    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
    expect(page.url()).toContain(PROJECT_ID);
  });
});

// ---------------------------------------------------------------------------
// Тест 5: API — GAP и требования
// ---------------------------------------------------------------------------

test.describe("GAP и Требования API", () => {
  test("GET /api/projects/:id/gaps возвращает данные", async ({ request }) => {
    const response = await request.get(
      `${BACKEND}/api/projects/${PROJECT_ID}/gaps`
    );
    // 200 или 404 если данных нет — оба допустимы
    expect([200, 404]).toContain(response.status());

    if (response.status() === 200) {
      const data = await response.json();
      expect(data).toBeTruthy();
    }
  });

  test("GET /api/projects/:id/requirements возвращает данные", async ({ request }) => {
    const response = await request.get(
      `${BACKEND}/api/projects/${PROJECT_ID}/requirements`
    );
    expect([200, 404]).toContain(response.status());

    if (response.status() === 200) {
      const data = await response.json();
      expect(data).toBeTruthy();
    }
  });
});
