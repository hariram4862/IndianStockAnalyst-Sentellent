import { create } from "zustand"
import { persist } from "zustand/middleware"

interface OnboardingState {
  hasSeenOnboarding: boolean
  hasHydrated: boolean
  activeStep: number | null
  start: () => void
  next: (totalSteps: number) => void
  dismiss: () => void
  setHasHydrated: (value: boolean) => void
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      hasSeenOnboarding: false,
      hasHydrated: false,
      activeStep: null,
      start: () => set({ activeStep: 0 }),
      next: (totalSteps) => {
        const current = get().activeStep ?? 0
        if (current + 1 >= totalSteps) {
          set({ activeStep: null, hasSeenOnboarding: true })
        } else {
          set({ activeStep: current + 1 })
        }
      },
      dismiss: () => set({ activeStep: null, hasSeenOnboarding: true }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "onboarding-storage",
      partialize: (state) => ({ hasSeenOnboarding: state.hasSeenOnboarding }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)
