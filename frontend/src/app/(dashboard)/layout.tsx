import AuthGuard from "@/components/auth/AuthGuard"
import Sidebar from "@/components/layout/Sidebar"
import Topbar from "@/components/layout/Topbar"
import { CommandPalette } from "@/components/command/command-palette"
import { StockDetailDrawer } from "@/components/stocks/stock-detail-drawer"
import { OnboardingTour } from "@/components/onboarding/onboarding-tour"
import { TooltipProvider } from "@/components/ui/tooltip"

export default function DashboardGroupLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <AuthGuard>
      <TooltipProvider>
        <div className="flex h-svh overflow-hidden">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <Topbar />
            <main className="min-h-0 min-w-0 flex-1 overflow-hidden">{children}</main>
          </div>
        </div>
        <CommandPalette />
        <StockDetailDrawer />
        <OnboardingTour />
      </TooltipProvider>
    </AuthGuard>
  )
}
