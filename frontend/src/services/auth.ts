import api from "./api";

export interface GoogleLoginRequest {
  id_token: string;
}

export const loginWithGoogle = async (idToken: string) => {
  const response = await api.post("/auth/google/login", {
    id_token: idToken,
  });

  return response.data;
};