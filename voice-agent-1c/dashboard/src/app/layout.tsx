import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Voice Agent 1C \u2014 \u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f",
  description: "\u0414\u0430\u0448\u0431\u043e\u0440\u0434 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0433\u043e AI-\u0430\u0433\u0435\u043d\u0442\u0430 \u0434\u043b\u044f \u0444\u0440\u0430\u043d\u0447\u0430\u0439\u0437\u0438 1\u0421",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
