import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-12 shrink-0 items-center gap-2 px-4">
          <SidebarTrigger className="-ml-1 text-muted-foreground hover:text-foreground transition-colors" />
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-6 mesh-bg grid-pattern">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
