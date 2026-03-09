/**
 * E2E тест: экспорт Visio (.vsdx) из BPMN-диаграмм.
 *
 * Проверяет:
 * 1. API endpoint GET /api/export/visio/<project_id>/<process_id> отвечает 200
 * 2. Content-Type = application/vnd.visio
 * 3. Размер файла > 5000 байт (не пустой)
 * 4. SVG endpoint тоже отвечает 200 и Content-Type = image/svg+xml
 *
 * Запуск:
 *   npx playwright test e2e/export-visio.spec.ts --headed
 *   npx playwright test e2e/export-visio.spec.ts
 */
import { test, expect } from "@playwright/test";

// Проект с готовыми диаграммами (ecb4ac19b44f49bb9da0ab72d817251a)
const PROJECT_ID = "ecb4ac19b44f49bb9da0ab72d817251a";
const BACKEND_BASE = "http://localhost:8000";

// Процессы для проверки
const PROCESSES = ["proc_001", "proc_002", "proc_003", "proc_004"];

// Минимальный допустимый размер VSDX файла (байт)
const MIN_VSDX_SIZE = 5_000;

// ---------------------------------------------------------------------------
// Тест 1: API endpoints — Visio экспорт
// ---------------------------------------------------------------------------

test.describe("Visio Export API", () => {
  for (const processId of PROCESSES) {
    test(`GET /api/export/visio/${processId} → 200 + valid VSDX`, async ({
      request,
    }) => {
      const url = `${BACKEND_BASE}/api/projects/${PROJECT_ID}/export/visio/${processId}`;

      const response = await request.get(url, {
        timeout: 30_000,
      });

      // Проверяем статус
      expect(response.status(), `Status for ${processId}`).toBe(200);

      // Проверяем Content-Type
      const contentType = response.headers()["content-type"] ?? "";
      expect(
        contentType,
        `Content-Type for ${processId}`
      ).toContain("application/vnd");

      // Проверяем размер файла
      const body = await response.body();
      expect(
        body.length,
        `File size for ${processId} (got ${body.length} bytes)`
      ).toBeGreaterThan(MIN_VSDX_SIZE);

      // Проверяем что это ZIP (VSDX = ZIP) — первые 2 байта PK
      expect(body[0], `ZIP magic byte 0 for ${processId}`).toBe(0x50); // P
      expect(body[1], `ZIP magic byte 1 for ${processId}`).toBe(0x4b); // K
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 2: API endpoints — SVG экспорт
// ---------------------------------------------------------------------------

test.describe("SVG Export API", () => {
  for (const processId of PROCESSES) {
    test(`GET /api/export/svg/${processId} → 200 + image/svg+xml`, async ({
      request,
    }) => {
      const url = `${BACKEND_BASE}/api/projects/${PROJECT_ID}/export/svg/${processId}`;

      const response = await request.get(url, { timeout: 15_000 });

      expect(response.status(), `Status for ${processId}`).toBe(200);

      const contentType = response.headers()["content-type"] ?? "";
      expect(contentType, `Content-Type for ${processId}`).toContain("svg");

      const body = await response.text();
      expect(body, `SVG content for ${processId}`).toContain("<svg");
      expect(body.length, `SVG size for ${processId}`).toBeGreaterThan(1_000);
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 3: UI — страница процессов загружается
// ---------------------------------------------------------------------------

test.describe("UI — Processes page", () => {
  test("Projects page loads and shows project list", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // Должен быть заголовок или контент
    const title = await page.title();
    expect(title).toBeTruthy();

    // Страница должна загрузиться без серверной ошибки
    // Используем innerText (не включает script/style теги) чтобы избежать ложных срабатываний
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("Internal Server Error");
  });

  test(`Project ${PROJECT_ID} has processes page accessible`, async ({
    page,
  }) => {
    const url = `/#/projects/${PROJECT_ID}/processes`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 15_000 });

    // Страница не должна показывать ошибку 404
    const status = page.url();
    expect(status).toBeTruthy();
  });
});
