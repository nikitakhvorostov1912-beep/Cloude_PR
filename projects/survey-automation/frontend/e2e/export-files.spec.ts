/**
 * E2E тест: экспорт всех типов файлов.
 *
 * Проверяет:
 * 1. Visio VSDX — /api/projects/:id/export/visio/:proc_id
 * 2. SVG preview — /api/projects/:id/export/svg/:proc_id
 * 3. BPMN XML — /api/projects/:id/export/bpmn/:proc_id
 * 4. Word (описания процессов) — /api/projects/:id/export/process-doc
 * 5. Excel (требования) — /api/projects/:id/export/requirements-excel
 * 6. Word (требования) — /api/projects/:id/export/requirements-word
 * 7. GAP-отчёт Excel — /api/projects/:id/export/gap-report
 * 8. ZIP всё — /api/projects/:id/export/all
 */
import { test, expect } from "@playwright/test";

const PROJECT_ID = "ecb4ac19b44f49bb9da0ab72d817251a";
const BACKEND = "http://localhost:8000";
const BASE = `${BACKEND}/api/projects/${PROJECT_ID}/export`;

const PROCESSES = ["proc_001", "proc_002", "proc_003", "proc_004"];

// ---------------------------------------------------------------------------
// Тест 1: Visio VSDX экспорт
// ---------------------------------------------------------------------------

test.describe("Экспорт Visio (.vsdx)", () => {
  for (const procId of PROCESSES) {
    test(`${procId} → 200, VSDX (ZIP magic PK), > 5KB`, async ({ request }) => {
      const response = await request.get(`${BASE}/visio/${procId}`, {
        timeout: 30_000,
      });

      expect(response.status(), `HTTP статус для ${procId}`).toBe(200);

      const ct = response.headers()["content-type"] ?? "";
      expect(ct, `Content-Type для ${procId}`).toContain("application/vnd");

      const body = await response.body();
      expect(body.length, `Размер VSDX ${procId}: ${body.length} байт`).toBeGreaterThan(5_000);

      // VSDX — это ZIP: начинается с PK (0x50 0x4B)
      expect(body[0], `ZIP magic[0] для ${procId}`).toBe(0x50);
      expect(body[1], `ZIP magic[1] для ${procId}`).toBe(0x4b);
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 2: SVG preview экспорт
// ---------------------------------------------------------------------------

test.describe("Экспорт SVG (preview)", () => {
  for (const procId of PROCESSES) {
    test(`${procId} → 200, image/svg+xml, содержит <svg>`, async ({ request }) => {
      const response = await request.get(`${BASE}/svg/${procId}`, {
        timeout: 20_000,
      });

      expect(response.status(), `HTTP статус для ${procId}`).toBe(200);

      const ct = response.headers()["content-type"] ?? "";
      expect(ct, `Content-Type для ${procId}`).toContain("svg");

      const body = await response.text();
      expect(body, `SVG содержимое ${procId}`).toContain("<svg");
      expect(body.length, `Размер SVG ${procId}`).toBeGreaterThan(1_000);
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 3: BPMN XML экспорт
// ---------------------------------------------------------------------------

test.describe("Экспорт BPMN XML", () => {
  for (const procId of PROCESSES) {
    test(`${procId} → 200, XML, содержит bpmn теги`, async ({ request }) => {
      const response = await request.get(`${BASE}/bpmn/${procId}`, {
        timeout: 15_000,
      });

      expect(response.status(), `HTTP статус для ${procId}`).toBe(200);

      const body = await response.text();
      expect(body, `BPMN содержимое ${procId}`).toContain("bpmn");
      expect(body.length, `Размер BPMN ${procId}`).toBeGreaterThan(500);
    });
  }
});

// ---------------------------------------------------------------------------
// Тест 4: Word документ (описания процессов)
// ---------------------------------------------------------------------------

test.describe("Экспорт Word (описания процессов)", () => {
  test("GET /export/process-doc → 200, docx (ZIP magic PK)", async ({ request }) => {
    const response = await request.get(`${BASE}/process-doc`, {
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);

    const ct = response.headers()["content-type"] ?? "";
    // Word docx — это Office Open XML
    expect(ct).toContain("application");

    const body = await response.body();
    expect(body.length).toBeGreaterThan(1_000);

    // DOCX — это ZIP: начинается с PK (0x50 0x4B)
    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);
  });
});

// ---------------------------------------------------------------------------
// Тест 5: Excel (требования)
// ---------------------------------------------------------------------------

test.describe("Экспорт Excel (требования)", () => {
  test("GET /export/requirements-excel → 200, xlsx (ZIP magic PK)", async ({ request }) => {
    const response = await request.get(`${BASE}/requirements-excel`, {
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);

    const body = await response.body();
    expect(body.length).toBeGreaterThan(1_000);

    // XLSX — это ZIP: начинается с PK
    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);
  });
});

// ---------------------------------------------------------------------------
// Тест 6: Word (требования)
// ---------------------------------------------------------------------------

test.describe("Экспорт Word (требования)", () => {
  test("GET /export/requirements-word → 200, docx (ZIP magic PK)", async ({ request }) => {
    const response = await request.get(`${BASE}/requirements-word`, {
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);

    const body = await response.body();
    expect(body.length).toBeGreaterThan(1_000);

    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);
  });
});

// ---------------------------------------------------------------------------
// Тест 7: GAP-отчёт Excel
// ---------------------------------------------------------------------------

test.describe("Экспорт GAP-отчёт (Excel)", () => {
  test("GET /export/gap-report → 200, xlsx (ZIP magic PK)", async ({ request }) => {
    const response = await request.get(`${BASE}/gap-report`, {
      timeout: 30_000,
    });

    expect(response.status()).toBe(200);

    const body = await response.body();
    expect(body.length).toBeGreaterThan(1_000);

    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);
  });
});

// ---------------------------------------------------------------------------
// Тест 8: ZIP (все файлы)
// ---------------------------------------------------------------------------

test.describe("Экспорт ZIP (все файлы)", () => {
  test("GET /export/all → 200, ZIP magic PK, > 20KB", async ({ request }) => {
    const response = await request.get(`${BASE}/all`, {
      timeout: 60_000,
    });

    expect(response.status()).toBe(200);

    const ct = response.headers()["content-type"] ?? "";
    expect(ct).toContain("zip");

    const body = await response.body();
    // ZIP со всеми файлами должен быть существенного размера
    expect(body.length).toBeGreaterThan(20_000);

    // ZIP magic bytes
    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);
  });
});
