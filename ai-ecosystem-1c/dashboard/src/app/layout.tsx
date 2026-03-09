import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AuroraBackground } from "@/components/aurora-background";
import { NoiseBackground } from "@/components/noise-background";
import { LayoutShell } from "@/components/layout-shell";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Аврора — Панель суфлёра",
  description: "AI-панель для менеджера: real-time транскрипт, автоклассификация, задачи",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          {/* Aurora animated background */}
          <AuroraBackground />

          {/* Noise/grain texture overlay */}
          <NoiseBackground />

          {/* Layout shell with TopNav + CommandPalette */}
          <LayoutShell>{children}</LayoutShell>
        </Providers>
      </body>
    </html>
  );
}
