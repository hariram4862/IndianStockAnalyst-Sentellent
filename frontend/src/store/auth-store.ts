import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: number;
  email: string;
  full_name: string;
  profile_picture?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  hasHydrated: boolean;

  login: (token: string, user: User) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hasHydrated: false,

      login: (token, user) =>
        set({
          token,
          user,
        }),

      logout: () =>
        set({
          token: null,
          user: null,
        }),

      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "auth-storage",
      // Guards (AuthGuard/GuestGuard) must not decide anything based on
      // `token` until this flips true -- persist rehydrates from
      // localStorage asynchronously, so the store's initial render is
      // always token=null even for a logged-in user, which otherwise
      // triggers a bogus redirect on every hard page load.
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
