/**
 * Authentication service for AuditEng V2
 */
import api from './api';

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface SessionInfo {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface User {
  id: string;
  email: string;
  is_admin: boolean;
}

// Decode JWT token to get user info
function decodeToken(token: string): User | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return {
      id: payload.sub,
      email: payload.email,
      is_admin: payload.is_admin || false,
    };
  } catch {
    return null;
  }
}

export const authService = {
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', credentials);
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } finally {
      localStorage.removeItem('access_token');
    }
  },

  async getSessions(): Promise<SessionInfo[]> {
    const response = await api.get<SessionInfo[]>('/auth/sessions');
    return response.data;
  },

  async changePassword(data: PasswordChangeRequest): Promise<void> {
    await api.post('/auth/change-password', data);
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/auth/forgot-password', { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },

  getCurrentUser(): User | null {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    return decodeToken(token);
  },

  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    if (!token) return false;

    // Check if token is expired
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000; // Convert to milliseconds
      return Date.now() < exp;
    } catch {
      return false;
    }
  },
};

export default authService;
