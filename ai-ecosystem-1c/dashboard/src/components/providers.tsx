"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Toaster } from "sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchInterval: 5000,
            staleTime: 3000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "rgba(13, 17, 51, 0.8)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(125, 190, 244, 0.12)",
            color: "#F1F5F9",
          },
        }}
      />
    </QueryClientProvider>
  );
}
