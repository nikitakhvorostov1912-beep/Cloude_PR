import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright конфигурация для E2E тестов Survey Automation.
 * Тестирует экспорт Visio, SVG preview и другие UI функции.
 */
export default defineConfig({
  testDir: "./e2e",
  /* Параллельный запуск тестов */
  fullyParallel: false,
  /* Не продолжать при ошибках в CI */
  forbidOnly: !!process.env.CI,
  /* Повторные попытки при ошибках */
  retries: process.env.CI ? 2 : 0,
  /* Только 1 воркер (нет параллелизма) */
  workers: 1,
  /* HTML отчёт */
  reporter: [["html", { open: "never" }], ["line"]],

  use: {
    /* Базовый URL фронтенда */
    baseURL: "http://localhost:3000",
    /* Скриншоты при ошибках */
    screenshot: "only-on-failure",
    /* Трассировка при ошибках */
    trace: "on-first-retry",
    /* Таймаут действий */
    actionTimeout: 15000,
    /* Таймаут навигации */
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Запуск dev-сервера перед тестами — НЕ нужен, запускаем вручную */
  // webServer: { command: "npm run dev", url: "http://localhost:3000" },
});
