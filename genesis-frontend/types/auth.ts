export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResult {
  success: boolean;
  error?: string;
  data?: TokenResponse;
}

export interface LoginState {
  error?: string;
  success?: boolean;
  fieldErrors?: {
    username?: string;
    password?: string;
  };
}

export interface LogoutState {
  error?: string;
  success?: boolean;
}

export interface RegisterState {
  success?: boolean;
  error?: string;
  fieldErrors?: {
    username?: string[];
    email?: string[];
    password?: string[];
    full_name?: string[];
    confirmPassword?: string[];
  };
}
