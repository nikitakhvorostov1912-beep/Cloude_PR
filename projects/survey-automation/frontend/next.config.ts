import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output для десктопного приложения
  // При NEXT_STANDALONE=1 создаёт самодостаточный сервер без node_modules
  ...(process.env.NEXT_STANDALONE === "1" && { output: "standalone" }),

  // URL backend API (для desktop: динамический порт)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
