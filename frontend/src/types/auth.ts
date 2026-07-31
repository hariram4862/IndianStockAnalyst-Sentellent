export interface User {
  id: number;
  email: string;
  full_name: string;
  profile_picture?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}