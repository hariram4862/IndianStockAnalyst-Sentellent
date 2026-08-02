import axios from "axios";
import { useAuthStore } from "@/store/auth-store";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Without this, an expired/invalid JWT (e.g. after ACCESS_TOKEN_EXPIRE_MINUTES,
// or a stale token left over from before a JWT_SECRET rotation) makes every
// authenticated request 401 forever -- AuthGuard only checks that a token
// *exists* in the persisted store, not that it's still valid, so the app was
// stuck rendering an empty dashboard with no recovery path. Clear the stale
// session and force a real re-login instead.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const hadToken = useAuthStore.getState().token !== null;
    if (error.response?.status === 401 && hadToken && typeof window !== "undefined") {
      useAuthStore.getState().logout();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login?sessionExpired=1";
      }
    }
    return Promise.reject(error);
  }
);

export default api;